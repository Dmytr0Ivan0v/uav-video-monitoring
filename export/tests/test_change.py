import cv2
import numpy as np

from site_export.change import mask_at, mask_levels

TAUS = [8, 12, 16, 20, 24]


def test_levels_give_back_the_mask_of_every_threshold():
    # made-up difference image: three square blobs of different strength and some thin noise
    diff = np.zeros((60, 90), np.uint8)
    diff[5:25, 5:25] = 10
    diff[30:55, 30:55] = 18
    diff[10:40, 60:85] = 30
    diff[::7, :] = 40       # one pixel lines: the opening removes them at every threshold
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))

    levels = mask_levels(diff, TAUS, 9)

    for k, tau in enumerate(TAUS):
        assert np.array_equal(levels > k, mask_at(diff, tau, kernel) > 0), f'tau {tau}'
    assert levels[15, 15] == 1      # 10 passes tau 8 only
    assert levels[42, 42] == 3      # 18 passes 8, 12, 16
    assert levels[25, 70] == 5
