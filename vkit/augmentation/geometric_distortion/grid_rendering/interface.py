class PointProjector:

    def project_point(self, src_point):
        raise NotImplementedError()

    def project_points(self, src_points):
        # For perf optimization.
        dst_points = []
        for src_point in src_points:
            dst_points.append(self.project_point(src_point))
        return dst_points
