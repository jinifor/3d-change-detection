class StorageKeys:
    @staticmethod
    def raw_t1(project_id: str) -> str:
        return f"project/{project_id}/raw/t1.laz"

    @staticmethod
    def raw_t2(project_id: str) -> str:
        return f"project/{project_id}/raw/t2.laz"

    @staticmethod
    def copc_t1(project_id: str) -> str:
        return f"project/{project_id}/copc/t1.copc.laz"

    @staticmethod
    def copc_t2_aligned(project_id: str) -> str:
        return f"project/{project_id}/copc/t2_aligned.copc.laz"

    @staticmethod
    def result_change_copc(project_id: str) -> str:
        return f"project/{project_id}/results/change.copc.laz"

    @staticmethod
    def result_change_geojson(project_id: str) -> str:
        return f"project/{project_id}/results/change.geojson"
