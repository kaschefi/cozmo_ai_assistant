from PIL import Image, ImageDraw, ImageFont
import pycozmo

class FaceLibrary:
    def __init__(self, cli):
        self.cli = cli
        self.width = 128
        self.height = 64

    def _get_base_canvas(self):
        return Image.new('1', (self.width, self.height), 0)

    def act_timer(self, time_str):
        img = self._get_base_canvas()
        draw = ImageDraw.Draw(img)
        # Big centered text
        draw.text((45, 25), time_str, fill=1)
        self.cli.display_image(img)

    def act_weather(self, temp, condition):
        img = self._get_base_canvas()
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"Vienna: {temp}", fill=1)
        self.cli.display_image(img)

    def act_thinking(self):
        img = self._get_base_canvas()
        draw = ImageDraw.Draw(img)
        draw.text((35, 25), "THINKING...", fill=1)
        self.cli.display_image(img)

    def act_reset(self):
        """Returns Cozmo to his standard eyes"""
        # Sending an empty image or calling a native animation resets the face
        self.cli.play_anim_group('NeutralFace')