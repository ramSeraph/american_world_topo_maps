import json
from pathlib import Path
from PIL import Image
from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor

foundation_predictor = FoundationPredictor()
recognition_predictor = RecognitionPredictor(foundation_predictor)
detection_predictor = DetectionPredictor()

txt_dir = Path('data/text')
for p in Path('data/raw').glob('*.jpg'):
    print(f'Processing {p.name}...')
    txt_file = txt_dir / f'{p.stem}.json'
    if txt_file.exists():
        print(f'Skipping {p.name}, already processed.')
        continue
    image = Image.open(p)

    predictions = recognition_predictor([image], det_predictor=detection_predictor)
    prediction = predictions[0]
    textlines = prediction.text_lines
    all_texts = []
    for textline in textlines:
        item = { 'text': textline.text, 'confidence': textline.confidence, 'polygon': textline.polygon }
        all_texts.append(item)

    with open(txt_file, 'w') as f:
        json.dump(all_texts, f, indent=4)

