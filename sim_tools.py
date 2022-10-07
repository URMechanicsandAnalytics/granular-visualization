import granular_bed.bed_tools


class SimParams:
    """
    Class to capture the state of the granular bed in the simulation
    """

    def __init__(self, filepath: str) -> None:
        self.__bed_oper = _SimFileOperators(filepath)

        self.box_width, self.box_height = self.__bed_oper.get_box_dims()

        self.timesteps = self.__bed_oper.get_timesteps()
        self.num_particles = self.__bed_oper.get_num_particles()
        self.DIM_OFFSET = self.__bed_oper.get_dim_idx()
        self.DATA_OFFSET = self.__bed_oper.get_data_idx()
        self.fields = self.__bed_oper.get_available_fields()

        # the initial state of the bed in the simulation
        self.initial_state: granular_bed.bed_tools.Bed = self.__bed_oper.get_bed_snap()
        self.initial_state_scaled: granular_bed.bed_tools.Bed = self.__bed_oper.get_bed_snap(absolute_coords=False)

        self.DISC_ID = self.__bed_oper.disc_id

    def get_bed_oper(self):
        return self.__bed_oper


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
                     absolute_coords=True):
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

        data_idx = self.get_data_idx()
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

                    out[p_ID] = data_values
                data_idx += 1
        except IndexError:
            pass
        # removing the disc
        if not out.pop(self.disc_id, True):
            raise KeyError

        return granular_bed.bed_tools.Bed(out)
