import os
import json
import base64
import mimetypes
import io
from pathlib import Path
from PIL import Image

def aggregate_data(questions_dir, output_file, image_base_url=None, embed_images=False, quality=100):
    questions_path = Path(questions_dir)
    subjects_data = []

    # Iterate through subject folders
    for subject_dir in sorted(questions_path.iterdir()):
        if not subject_dir.is_dir():
            continue
        
        # Skip hidden folders and known non-subject folders
        if subject_dir.name.startswith('.') or subject_dir.name in ['web', 'scripts', 'misc']:
            continue

        subject_json_path = subject_dir / "subject.json"
        if not subject_json_path.exists():
            # Only warn if it looks like it should be a subject (has a questions subfolder)
            if (subject_dir / "questions").exists():
                print(f"Warning: No subject.json found in {subject_dir}")
            continue

        with open(subject_json_path, 'r', encoding='utf-8') as f:
            subject_info = json.load(f)

        subject_questions = []
        questions_subdir = subject_dir / "questions"
        
        if questions_subdir.exists() and questions_subdir.is_dir():
            # Iterate through individual question folders
            for q_dir in sorted(questions_subdir.iterdir()):
                if not q_dir.is_dir():
                    continue
                
                q_json_path = q_dir / "question.json"
                if q_json_path.exists():
                    with open(q_json_path, 'r', encoding='utf-8') as f:
                        try:
                            q_data = json.load(f)
                            q_data['id'] = q_dir.name
                            q_data['subjectCode'] = subject_info.get('code')
                            
                            # Detect images
                            image_extensions = ('.png', '.jpg', '.jpeg', '.svg', '.webp')
                            image_files = [f for f in q_dir.iterdir() if f.suffix.lower() in image_extensions]
                            
                            if image_files:
                                # Prioritize 'quiz.png' or the first image found
                                main_image = next((f for f in image_files if f.name.lower() == 'quiz.png'), image_files[0])
                                
                                if embed_images:
                                    # Convert image to Base64 with optional compression
                                    try:
                                        with Image.open(main_image) as img:
                                            # Skip compression for SVGs as they are text-based
                                            if main_image.suffix.lower() == '.svg':
                                                with open(main_image, "rb") as svg_file:
                                                    encoded_string = base64.b64encode(svg_file.read()).decode('utf-8')
                                                mime_type = "image/svg+xml"
                                            else:
                                                buffer = io.BytesIO()
                                                # If quality is less than 100, we use WebP for much better compression
                                                # even if the source was PNG (it's for web delivery after all)
                                                if quality < 100:
                                                    img.save(buffer, format="WEBP", quality=quality, method=6)
                                                    mime_type = "image/webp"
                                                else:
                                                    # Just optimize the original format
                                                    fmt = img.format if img.format else 'PNG'
                                                    img.save(buffer, format=fmt, optimize=True)
                                                    mime_type = f"image/{fmt.lower()}"
                                                
                                                encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
                                            
                                            # Use quizPhoto for images named quiz.png, otherwise use photo
                                            field_name = 'quizPhoto' if main_image.name.lower().startswith('quiz') else 'photo'
                                            q_data[field_name] = f"data:{mime_type};base64,{encoded_string}"
                                    except Exception as e:
                                        print(f"Warning: Could not process image {main_image}: {e}")
                                        # Fallback to raw copy if Pillow fails
                                        with open(main_image, "rb") as img_file:
                                            encoded_string = base64.b64encode(img_file.read()).decode('utf-8')
                                            mime_type, _ = mimetypes.guess_type(main_image)
                                            field_name = 'quizPhoto' if main_image.name.lower().startswith('quiz') else 'photo'
                                            q_data[field_name] = f"data:{mime_type};base64,{encoded_string}"
                                else:
                                    rel_path = f"{subject_dir.name}/questions/{q_dir.name}/{main_image.name}"
                                    field_name = 'quizPhoto' if main_image.name.lower().startswith('quiz') else 'photo'
                                    if image_base_url:
                                        q_data[field_name] = f"{image_base_url.rstrip('/')}/{rel_path}"
                                    else:
                                        q_data[field_name] = rel_path
                            
                            subject_questions.append(q_data)
                        except json.JSONDecodeError:
                            print(f"Error decoding JSON in {q_json_path}")

        # Combine subject info with its questions
        subject_info['questions'] = subject_questions
        subjects_data.append(subject_info)

    # Wrap in root object
    final_data = {
        "subjects": subjects_data,
        "generatedAt": Path(output_file).name, # Just a placeholder or timestamp
        "version": "1.0.0"
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully generated {output_file} with {len(subjects_data)} subjects.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Aggregate questions and metadata into a single JSON file.')
    parser.add_argument('--image-base', help='Base URL for images (e.g., https://raw.githubusercontent.com/user/repo/main/questions/)')
    parser.add_argument('--embed', action='store_true', help='Embed images directly into the JSON as Base64 data URIs')
    parser.add_argument('--quality', type=int, default=100, help='Quality percentage for compressed images (1-100). Only used with --embed.')
    args = parser.parse_args()

    # Robust path detection
    current_dir = Path(__file__).parent.resolve()
    # ... existing detection logic ...
    if (current_dir / "aag").exists() and not (current_dir / "subject.json").exists():
        # We are likely already in the questions folder
        agg_questions_dir = current_dir
        ROOT_DIR = current_dir.parent
    elif (current_dir / "questions").exists():
        # We are in the project root
        agg_questions_dir = current_dir / "questions"
        ROOT_DIR = current_dir
    else:
        # Fallback to previous logic
        if current_dir.name == "scripts":
            ROOT_DIR = current_dir.parent.parent
        elif current_dir.name == "questions":
            ROOT_DIR = current_dir.parent
        else:
            ROOT_DIR = current_dir
        agg_questions_dir = ROOT_DIR / "questions"

    agg_output_file = ROOT_DIR / "questions" / "questions.json"
    
    # Ensure output directory exists
    agg_output_file.parent.mkdir(parents=True, exist_ok=True)
    
    aggregate_data(agg_questions_dir, agg_output_file, image_base_url=args.image_base, embed_images=args.embed, quality=args.quality)
