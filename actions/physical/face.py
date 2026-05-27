from PIL import Image, ImageDraw, ImageFont
import pycozmo

class FaceLibrary:
    def __init__(self, cli):
        self.cli = cli
        self.width = 128
        self.height = 32  # Cozmo screen height is strictly 32 pixels!

    def _get_base_canvas(self):
        return Image.new('1', (self.width, self.height), 0)

    def act_timer(self, time_str):
        """Draws a beautiful timer with a centered clock icon on 128x32 OLED"""
        img = self._get_base_canvas()
        draw = ImageDraw.Draw(img)
        
        # Load standard system font
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font = ImageFont.load_default()
            
        # Draw clock icon on the left (Centered vertically at cy=16)
        cx, cy = 30, 16
        draw.ellipse((cx-10, cy-10, cx+10, cy+10), outline=1, width=1)
        draw.line((cx, cy, cx, cy-6), fill=1, width=1)   # Hour hand
        draw.line((cx, cy, cx+5, cy), fill=1, width=1)   # Minute hand
        
        # Draw the big centered time text on the right
        draw.text((60, 4), time_str, font=font, fill=1)
        
        self.cli.display_image(img)

    def act_weather(self, temp, condition):
        """
        Premium weather display on Cozmo's 128x32 OLED:
        - Left Side: Smaller elegant temperature reading (e.g. 14 C)
        - Center: Open, divider-free layout
        - Right Side: Custom-drawn, enlarged thematic pixel icon (centered at cx=85, cy=16)
        """
        img = self._get_base_canvas()
        draw = ImageDraw.Draw(img)

        # 1. Load system fonts
        try:
            temp_font = ImageFont.truetype("arial.ttf", 12)
            unit_font = ImageFont.truetype("arial.ttf", 8)
        except IOError:
            temp_font = ImageFont.load_default()
            unit_font = ImageFont.load_default()

        # 2. Draw Left Side: Temperature Reading
        # Normalize temp format
        clean_temp = str(temp).replace("+", "").replace("-", "").strip()
        is_negative = str(temp).startswith("-")
        
        display_text = f"-{clean_temp}" if is_negative else clean_temp
        draw.text((10, 10), display_text, font=temp_font, fill=1)
        
        # Safely measure text width (fully exception-proof across PIL versions)
        try:
            if hasattr(draw, 'textlength'):
                num_width = int(draw.textlength(display_text, font=temp_font))
            elif hasattr(temp_font, 'getlength'):
                num_width = int(temp_font.getlength(display_text))
            else:
                num_width = len(display_text) * 7
        except Exception:
            num_width = len(display_text) * 7
        
        # Draw the tiny degree circle manually (100% safe from font encoding crashes on default fonts!)
        deg_x = 10 + num_width + 2
        draw.ellipse((deg_x, 8, deg_x + 2, 10), outline=1)
        
        # Draw the letter "C"
        draw.text((deg_x + 5, 8), "C", font=unit_font, fill=1)

        # 3. Draw Right Side: Custom Enlarged Weather Thematic Icon
        cond = str(condition).lower().strip()
        cx, cy = 85, 16  # Center shifted to 85 to occupy more center-right screen space

        if cond == "sunny":
            # Drawing an enlarged radiating Sun
            draw.ellipse((cx-7, cy-7, cx+7, cy+7), outline=1, width=1)
            # Drawing sun rays
            ray_length = 13
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-0.7,-0.7), (0.7,0.7), (-0.7,0.7), (0.7,-0.7)]:
                draw.line((cx + dx*8, cy + dy*8, cx + dx*ray_length, cy + dy*ray_length), fill=1, width=1)
                
        elif cond == "cloudy":
            # Drawing a larger compound cloud
            draw.ellipse((cx-14, cy-2, cx-3, cy+11), fill=1)
            draw.ellipse((cx-6, cy-9, cx+8, cy+11), fill=1)
            draw.ellipse((cx+5, cy-2, cx+14, cy+11), fill=1)
            
        elif cond == "rainy":
            # Drawing a larger cloud with longer falling raindrops
            draw.ellipse((cx-11, cy-5, cx-3, cy+5), fill=1)
            draw.ellipse((cx-6, cy-11, cx+7, cy+5), fill=1)
            draw.ellipse((cx+5, cy-5, cx+11, cy+5), fill=1)
            # Rain drops
            draw.line((cx-7, cy+7, cx-9, cy+13), fill=1, width=1)
            draw.line((cx-2, cy+7, cx-4, cy+13), fill=1, width=1)
            draw.line((cx+3, cy+7, cx+1, cy+13), fill=1, width=1)
            draw.line((cx+8, cy+7, cx+6, cy+13), fill=1, width=1)
            
        elif cond == "snowy":
            # Drawing a larger snowflake structure
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (0.7,0.7), (-0.7,-0.7), (0.7,-0.7), (-0.7,0.7)]:
                draw.line((cx, cy, cx + dx*12, cy + dy*12), fill=1, width=1)
                
        elif cond == "stormy":
            # Drawing a larger sharp lightning bolt
            bolt_coords = [
                (cx+5, cy-14),
                (cx-6, cy+1),
                (cx+2, cy+1),
                (cx-4, cy+15),
                (cx+10, cy-1),
                (cx+2, cy-1)
            ]
            draw.polygon(bolt_coords, fill=1)
            
        else:
            # Default / Foggy: Render three longer horizontal wind lines
            draw.line((cx-16, cy-6, cx+16, cy-6), fill=1, width=1)
            draw.line((cx-10, cy, cx+10, cy), fill=1, width=1)
            draw.line((cx-16, cy+6, cx+16, cy+6), fill=1, width=1)

        self.cli.display_image(img)

    def act_thinking(self):
        """Draws a beautiful thinking screen on 128x32 OLED"""
        img = self._get_base_canvas()
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 10)
        except IOError:
            font = ImageFont.load_default()
            
        # Draw a beautiful bordered thinking box (with rounded rectangle fallback)
        if hasattr(draw, 'rounded_rectangle'):
            draw.rounded_rectangle((15, 4, 113, 28), radius=3, outline=1, width=1)
        else:
            draw.rectangle((15, 4, 113, 28), outline=1, width=1)
            
        draw.text((36, 10), "THINKING...", font=font, fill=1)
        self.cli.display_image(img)

    def act_reset(self):
        """Returns Cozmo to his standard eyes by drawing them customly (bypasses missing anim group errors)"""
        img = self._get_base_canvas()
        draw = ImageDraw.Draw(img)
        
        # Left eye capsule (with rounded rectangle fallback)
        if hasattr(draw, 'rounded_rectangle'):
            draw.rounded_rectangle((32, 6, 52, 26), radius=5, fill=1)
            draw.rounded_rectangle((76, 6, 96, 26), radius=5, fill=1)
        else:
            draw.rectangle((32, 6, 52, 26), fill=1)
            draw.rectangle((76, 6, 96, 26), fill=1)
        
        self.cli.display_image(img)