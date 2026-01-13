import json
from pathlib import Path

def aggregate_data(questions_dir, output_file, image_base_url="https://raw.githubusercontent.com/CoconutBigNut/cvut-otazky/refs/heads/main/questions"):
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
                                
                                rel_path = f"{subject_dir.name}/questions/{q_dir.name}/{main_image.name}"
                                field_name = 'quizPhoto' if main_image.name.lower().startswith('quiz') else 'photo'
                                q_data[field_name] = f"{image_base_url.rstrip('/')}/{rel_path}"
                            
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
    parser.add_argument('--image-base', default="https://raw.githubusercontent.com/CoconutBigNut/cvut-marasty/main/questions", help='Base URL for images (e.g., https://raw.githubusercontent.com/user/repo/main/questions/)')
    args = parser.parse_args()

    # Robust path detection
    current_dir = Path(__file__).parent.resolve()
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
    
    aggregate_data(agg_questions_dir, agg_output_file, image_base_url=args.image_base)

