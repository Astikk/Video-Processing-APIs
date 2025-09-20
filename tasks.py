from celery_app import celery
from services.video_services import add_video_overlay  # your existing overlay function

@celery.task(bind=True)
def overlay_video_task(self, input_path, overlay_path, output_path, x, y):
    try:
        add_video_overlay(input_path, overlay_path, output_path, x, y)
        return {"status": "success", "output_path": output_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}