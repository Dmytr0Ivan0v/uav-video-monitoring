import numpy as np

from site_export.vo import associate, quat_from_rot, rot_from_quat, umeyama_se3


def test_alignment_recovers_a_known_rotation_and_shift():
    rng = np.random.default_rng(0)
    src = rng.uniform(-1, 1, (50, 3))
    angle = np.radians(30)
    r_true = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    dst = src @ r_true.T + [0.5, -0.2, 1.4]

    r, t = umeyama_se3(src, dst)

    assert np.allclose(r, r_true)
    assert np.allclose(t, [0.5, -0.2, 1.4])


def test_quaternion_round_trip_keeps_w_non_negative():
    q = np.array([0.1, -0.7, 0.2, -0.6])
    q = q / np.linalg.norm(q)

    back = quat_from_rot(rot_from_quat(q))

    assert back[3] >= 0
    assert np.allclose(back, -q)


def test_association_takes_the_closest_pairs_once():
    est = np.array([0.000, 0.033, 0.066])
    gt = np.array([0.001, 0.030, 0.034, 0.100])

    # 0.033 is closer to 0.034 than to 0.030; 0.066 has no stamp within 0.02
    assert associate(est, gt, 0.02) == [(0, 0), (1, 2)]
