from site_export.gt import read_gt

# made-up rows in the VisDrone MOT layout: frame, target, x, y, w, h, score, category, truncation, occlusion
ROWS = """1,7,10,20,30,40,1,4,0,0
1,8,0,0,50,50,0,1,0,0
1,9,5,5,10,10,1,11,0,0
2,7,12,20,30,40,1,1,0,1
"""


def test_gt_skips_ignored_boxes_and_counts_frames_from_zero(tmp_path):
    path = tmp_path / 'clip.txt'
    path.write_text(ROWS, encoding='utf-8')

    frames = read_gt(path, {1: 0, 4: 2})

    assert frames == [
        {'frame': 0, 'boxes': [[7, 2, 10, 20, 40, 60]]},
        {'frame': 1, 'boxes': [[7, 0, 12, 20, 42, 60]]},
    ]
