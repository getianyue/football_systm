from deep_sort_realtime.deepsort_tracker import DeepSort

class PlayerTracker:
    def __init__(self):
        self.tracker = DeepSort(
            max_age=50,
            n_init=3,
            max_cosine_distance=0.4
        )

    def update(self, detections, frame):
        return self.tracker.update_tracks(detections, frame=frame)
