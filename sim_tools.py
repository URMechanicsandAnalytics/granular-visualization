from granular_vis.granular_bed.bed_tools import Bed
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
import numpy as np


class SimParams:
    """
    Class to capture the state of the granular bed in the simulation
    """

    def __init__(self, filepath: str) -> None:
        self.__bed_oper = _SimFileOperators(filepath)

        # the initial state of the bed in the simulation
        self.initial_state: Bed = Bed(self.__bed_oper.get_bed_snap())

        self.timesteps = self.__bed_oper.get_timesteps()
        self.num_timesteps = len(self.timesteps)

        self.num_particles = self.__bed_oper.get_num_particles()
        self.box_width, self.box_height = self.__bed_oper.get_box_dims()

        self.DIM_OFFSET = self.__bed_oper.get_dim_idx()
        self.DATA_OFFSET = self.__bed_oper.get_data_idx()
        self.DISC_ID = self.__bed_oper.disc_id
        self.fields = self.__bed_oper.get_available_fields()

    def initial_state_scaled(self) -> Bed:
        return Bed(self.__bed_oper.get_bed_snap(absolute_coords=False))

    def get_bed_static(self, idx: int = 0, absolute_coords=True, include_only=None) -> Bed:
        return Bed(self.__bed_oper.get_bed_snap(idx=idx, timestep=self.timesteps[idx]['value'],
                                                absolute_coords=absolute_coords,
                                                include_only=include_only))

    def get_bed_dynamic(self, idx: int = 0, absolute_coords=True, include_only=None) -> Bed:
        """
        Method to get the expanded data
        """
        out: dict = {}
        """
        p_ID : {
            ax : [...],
            vx : [...]
        },
        p_ID : {
            ax : [...],
            vx : [...]
        },
        ...
        """
        for p_ID, fields in self.render_bed.items():
            if include_only is not None:
                if p_ID not in include_only:
                    continue
            out[p_ID] = {
                field: f_array[idx]
                for field, f_array in fields.items()
            }

        return Bed(out)

    def render_bed_multi(self) -> None:
        self.render_bed = self.__bed_oper.read_timesteps_multi()
        self.differentiate()

    def render_bed_single(self) -> None:
        self.render_bed = self.__bed_oper.read_timesteps_single()
        self.differentiate()

    def get_bed_oper(self):
        return self.__bed_oper

    def differentiate(self) -> None:
        """
        Method to differentiate the x and y datas to get velocity and acceleration
        """
        num_timesteps = self.num_timesteps
        for time_data, value in self.render_bed.items():
            x = [i for i in value if i in ["xs", "x"]][0]
            y = [i for i in value if i in ["ys", "y"]][0]
            x_arr = value[x]
            y_arr = value[y]

            if x == 'x':
                v_x = np.gradient(x_arr, num_timesteps)
                self.render_bed[time_data]['v_x'] = v_x
                self.render_bed[time_data]['a_x'] = np.gradient(v_x, num_timesteps)
            elif x == "xs":
                vs_x = np.gradient(x_arr, num_timesteps)
                self.render_bed[time_data]['vs_x'] = vs_x
                self.render_bed[time_data]['as_x'] = np.gradient(vs_x, num_timesteps)

            if y == 'y':
                v_y = np.gradient(y_arr, num_timesteps)
                self.render_bed[time_data]['v_y'] = v_y
                self.render_bed[time_data]['a_y'] = np.gradient(v_y, num_timesteps)
            elif y == "ys":
                vs_y = np.gradient(y_arr, num_timesteps)
                self.render_bed[time_data]['vs_y'] = vs_y
                self.render_bed[time_data]['as_y'] = np.gradient(vs_y, num_timesteps)


class _SimFileOperators:
    """
    Defining the operators for the bed
    """

    def __init__(self, filepath: str) -> None:
        self.filepath: str = filepath

        with open(filepath, 'r') as input_file:
            lines = input_file.readlines()
        self.__lines = lines

    def get_num_particles(self) -> int:
        for i, line in enumerate(self.__lines):
            if "ITEM: NUMBER OF ATOMS" in line:
                return int(self.__lines[i + 1].split()[0])
        return -1

    def get_dim_idx(self) -> int:
        for i, line in enumerate(self.__lines):
            if "ITEM: BOX BOUNDS" in line:
                return i + 1  # 5
        return -1

    def get_data_idx(self) -> int:
        for i, line in enumerate(self.__lines):
            if "ITEM: ATOMS" in line:
                return i + 1  # 8
        return -1

    def get_available_fields(self) -> list[str]:
        for line in self.__lines:
            if "ITEM: ATOMS" in line:
                return [param for param in line.split()
                        if param not in "ITEM: ATOMS"
                        ]
        return []

    def get_box_dims(self):  # -> Generator[float]:
        dim_idx = self.get_dim_idx()
        return (
            float(line.split().pop(1))
            for line in self.__lines[dim_idx:dim_idx + 2]
        )

    def get_timesteps(self) -> dict[int, dict[str, int]]:
        out = {}
        i = 0
        for idx, line in enumerate(self.__lines):
            if "ITEM: TIMESTEP" in line:
                # TODO actual timestep value being used to query
                out[i] = {
                    "line": idx + 1,
                    "value": int(self.__lines[idx + 1].split()[0])
                }
                i += 1
        return out

    def get_bed_snap(self,
                     timestep=None, idx=None,
                     include_only=None,
                     absolute_coords=True,
                     array_form=False) -> dict:
        """
        Method to get the state of the bed at the specified timestep.
        """

        if include_only is None:
            include_only = []
        timesteps = self.get_timesteps()
        fields = self.get_available_fields()

        # setting default timestep values
        if idx is None:
            idx = 0
        if timestep is None:
            timestep = timesteps[0]["value"]

        # checking if the timestep is correct
        if timestep != int(self.__lines[timesteps[idx]['line']]):
            raise IndexError(
                f"The TIMESTEP at index {idx}, "
                f"line {timesteps[idx]['line']} "
                f"does not match the TIMESTEP passed in the argument: "
                f" {timesteps[idx]['value']}")

        data_idx = timesteps[idx]['line'] + self.get_data_idx()
        out: dict = {}
        self.disc_id = 0
        try:
            while "ITEM: TIMESTEP" not in self.__lines[data_idx]:
                data_line = self.__lines[data_idx].split()
                p_ID = int(data_line[0])
                if p_ID > self.disc_id:
                    self.disc_id = p_ID
                valid_particle = False

                if len(include_only) == 0:
                    valid_particle = True
                else:
                    if p_ID in include_only:
                        valid_particle = True
                    else:
                        data_idx += 1
                        continue

                # putting the values in a dictionary by parameter type
                if valid_particle:
                    data_values = {
                        p: float(data_line[fields.index(p)])
                        for p in fields if p != "id"
                    }
                    # converting to absolute coordinates
                    # throws KeyError if target key is not found
                    if absolute_coords:
                        # TODO for 3D simulations, scale it for the z-axis as well
                        box_w, box_h = self.get_box_dims()
                        try:
                            data_values["x"] = box_w * data_values["xs"]
                            if not data_values.pop("xs", True):
                                raise KeyError
                        except KeyError:
                            print(f"WARNING: key \'x\' was not found as a "
                                  f"parameter for particle {p_ID}!")
                        try:
                            data_values["y"] = box_h * data_values["ys"]
                            if not data_values.pop("ys", True):
                                raise KeyError
                        except KeyError:
                            print(f"WARNING: key \'y\' was not found as a "
                                  f"parameter for particle {p_ID}!")
                    if array_form:
                        data_values = {
                            p: [v]
                            for p, v in data_values.items()
                        }

                    out[p_ID] = data_values
                data_idx += 1
        except IndexError:
            pass
        # removing the disc
        if not out.pop(self.disc_id, True):
            raise KeyError

        return out

    def read_timesteps_multi(self):  # -> dict:
        out_multi = self.get_bed_snap(array_form=True)
        keys_not_added_multi = []

        timesteps = self.get_timesteps()
        ts = [t for t in timesteps]
        vs = [timesteps[t] for t in timesteps]

        def __add_entry_t(t, v):
            bed_snap = self.get_bed_snap(idx=t, timestep=v['value'], include_only=None)
            for p_ID, p_data in bed_snap.items():
                for f_name, f_value in p_data.items():
                    try:
                        out_multi[p_ID][f_name].append(f_value)
                    except KeyError:
                        keys_not_added_multi.append(f"{f_name:15s} for p{p_ID} at t{t}-->{v['value']} not added.")
                        pass

        workers = 4
        print(f"Testing Multithreading ({workers} workers)")
        start_multi = perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            executor.map(__add_entry_t, ts, vs)
        print("End Test Multithreading")
        end_multi = perf_counter()

        for msg in list(set(keys_not_added_multi)):
            print(msg)
        print(f"\nMulti Time: {end_multi - start_multi}")

        return out_multi

    def read_timesteps_single(self):
        out_single = self.get_bed_snap(array_form=True)
        keys_not_added_single = []
        timesteps = self.get_timesteps()

        print("Start Single")
        start_single = perf_counter()
        for t, v in timesteps.items():
            out_single, keys_not_added_single = self.__add_entry_t(out=out_single,
                                                                   t=t, v=v,
                                                                   keys_not_added=keys_not_added_single)
        print("End Test Single")
        end_single = perf_counter()
        for msg in list(set(keys_not_added_single)):
            print(msg)
        print(f"Single Time: {end_single - start_single}")

        return out_single

    def __add_entry_t(self, **kwargs) -> tuple:
        """
        Method to add a single entry to the rendered datafile
        """
        out = kwargs["out"]
        keys_not_added = kwargs["keys_not_added"]
        t = kwargs["t"]
        v = kwargs["v"]

        bed_snap = self.get_bed_snap(idx=t, timestep=v['value'], include_only=None)
        for p_ID, p_data in bed_snap.items():
            for f_name, f_value in p_data.items():
                try:
                    out[p_ID][f_name].append(f_value)
                    # print(f"Added {f_name:15s} for p{p_ID} at t{t}-->{v['value']}")
                except KeyError:
                    keys_not_added.append(f"{f_name:15s} for p{p_ID} at t{t}-->{v['value']} not added.")
                    pass
        # print("")

        return out, keys_not_added
