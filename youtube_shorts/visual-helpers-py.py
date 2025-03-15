"""
Helper functions for visual processing in YouTube Shorts Automation Framework.
These are top-level functions to be used by multiprocessing.
"""

import os
import re
from typing import List, Dict, Any, Tuple


def generate_frame_chunk(chunk_info: Tuple) -> int:
    """
    Worker function to generate a chunk of frames.
    This is a top-level function to make it picklable for multiprocessing.
    
    Args:
        chunk_info: Tuple containing frame generation parameters
        
    Returns:
        int: Number of frames generated
    """
    from PIL import Image, ImageDraw, ImageFont
    
    # Unpack the chunk info
    (start_frame, end_frame, font_path, width, height, 
     fps, frames_dir, bg_temp_path, timings) = chunk_info
    
    # Load background image
    bg = Image.open(bg_temp_path)
    
    # Set up font
    try:
        font = ImageFont.truetype(font_path, 70)
    except Exception:
        # Fallback to default font if loading fails
        font = ImageFont.load_default()
    
    # Process frames in this chunk
    generated_count = 0
    
    for frame_num in range(start_frame, end_frame):
        # Calculate time position for this frame
        time_position = frame_num / fps
        
        # Find which narration segment this frame belongs to
        current_segment = None
        for timing in timings:
            if timing['start_time'] <= time_position <= timing['end_time']:
                current_segment = timing
                break
        
        # Create frame based on time position
        if current_segment:
            # Calculate progress within this segment
            segment_duration = current_segment['duration']
            segment_progress = (time_position - current_segment['start_time']) / segment_duration
            
            # Create frame with text
            frame = create_text_frame(bg.copy(), current_segment['line'], font, 
                                    width, height, segment_progress)
        else:
            # Create blank frame if not in any segment
            frame = bg.copy()
        
        # Save frame
        frame = frame.convert("RGB")  # Convert to RGB for JPEG
        frame_path = os.path.join(frames_dir, f"frame_{frame_num:04d}.jpg")
        frame.save(frame_path, quality=90)
        generated_count += 1
    
    return generated_count


def create_text_frame(bg_img, text: str, font, width: int, height: int, progress_in_segment=0.5):
    """
    Create a frame with text overlay.
    This is a top-level function to make it picklable for multiprocessing.
    
    Args:
        bg_img: Background image
        text: Text to display
        font: Font object
        width: Frame width
        height: Frame height
        progress_in_segment: Progress within the current segment (0.0 to 1.0)
        
    Returns:
        PIL.Image: Frame with text overlay
    """
    from PIL import Image, ImageDraw
    
    # Copy the background
    img = bg_img.copy()
    draw = ImageDraw.Draw(img)
    
    # Parse numbered format (e.g. "1. **Title**: Content")
    point_number = None
    title = None
    content = text
    
    # Extract number and title if this is a numbered point
    match = re.match(r'^(\d+)[.:]\s', text)
    if match:
        point_number = match.group(1)
        title_match = re.search(r'^\d+[.:]\s+\*\*([^*]+)\*\*:?\s*', text)
        if title_match:
            title = title_match.group(1)
            content_match = re.search(r'^\d+[.:]\s+\*\*[^*]+\*\*:?\s*(.+)$', text, re.DOTALL)
            if content_match:
                content = content_match.group(1)
    
    # Special layout for numbered points
    if point_number and title:
        # Simplified version for parallel processing
        # Draw text in a standard layout
        wrapped_text = f"{point_number}. {title}: {content}"
        wrapped_lines = wrap_text(wrapped_text, font, draw, width - 120)
        
        text_height = len(wrapped_lines) * 80
        start_y = (height - text_height) // 2
        
        for k, line in enumerate(wrapped_lines):
            if hasattr(draw, 'textlength'):
                text_width = draw.textlength(line, font=font)
            else:
                text_width = draw.textsize(line, font=font)[0]
            
            # Center text
            text_x = (width - text_width) // 2
            text_y = start_y + k * 80
            
            # Simplified animation - just fade based on progress
            alpha = 255
            if progress_in_segment < 0.2:
                alpha = int(progress_in_segment * 5 * 255)
            elif progress_in_segment > 0.8:
                alpha = int((1 - progress_in_segment) * 5 * 255)
            
            # Draw a semi-transparent background
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([
                text_x - 20, text_y - 10,
                text_x + text_width + 20, text_y + 70
            ], fill=(0, 0, 0, min(128, alpha//2)))
            
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)
            
            # Draw text with outline
            for dx, dy in [(x, y) for x in [-2, 0, 2] for y in [-2, 0, 2] if not (x == 0 and y == 0)]:
                draw.text((text_x + dx, text_y + dy), line, font=font, fill=(0, 0, 0, alpha))
            
            # Draw the text
            draw.text((text_x, text_y), line, font=font, fill=(255, 255, 255, alpha))
    else:
        # Standard text rendering
        wrapped_lines = wrap_text(text, font, draw, width - 120)
        text_height = len(wrapped_lines) * 80
        start_y = (height - text_height) // 2
        
        for k, line in enumerate(wrapped_lines):
            if hasattr(draw, 'textlength'):
                text_width = draw.textlength(line, font=font)
            else:
                text_width = draw.textsize(line, font=font)[0]
            
            text_x = (width - text_width) // 2
            text_y = start_y + k * 80
            
            # Simple fade effect
            alpha = 255
            if progress_in_segment < 0.2:
                alpha = int(progress_in_segment * 5 * 255)
            elif progress_in_segment > 0.8:
                alpha = int((1 - progress_in_segment) * 5 * 255)
            
            # Draw background
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([
                text_x - 20, text_y - 10, 
                text_x + text_width + 20, text_y + 70
            ], fill=(0, 0, 0, min(128, alpha//2)))
            
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)
            
            # Draw text with outline
            for dx, dy in [(x, y) for x in [-2, 0, 2] for y in [-2, 0, 2] if not (x == 0 and y == 0)]:
                draw.text((text_x + dx, text_y + dy), line, font=font, fill=(0, 0, 0, alpha))
            
            # Draw the text
            draw.text((text_x, text_y), line, font=font, fill=(255, 255, 255, alpha))
    
    # Convert back to RGB for saving
    if img.mode == "RGBA":
        img = img.convert("RGB")
    
    return img


def wrap_text(text: str, font, draw, max_width: int) -> List[str]:
    """
    Wrap text to fit within max_width.
    This is a top-level function to make it picklable for multiprocessing.
    
    Args:
        text: The text to wrap
        font: Font object
        draw: ImageDraw object
        max_width: Maximum width in pixels
        
    Returns:
        List[str]: Lines of wrapped text
    """
    words = text.split()
    wrapped_lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        
        # Get text width - implementation varies by PIL version
        if hasattr(draw, 'textlength'):
            text_width = draw.textlength(test_line, font=font)
        else:
            text_width = draw.textsize(test_line, font=font)[0]
        
        if text_width < max_width:
            current_line.append(word)
        else:
            wrapped_lines.append(' '.join(current_line))
            current_line = [word]
    
    if current_line:
        wrapped_lines.append(' '.join(current_line))
    
    return wrapped_lines
