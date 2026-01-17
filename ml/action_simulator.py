def simulate(row, action):
    b = row["biometric_intensity"]
    c = row["child_bio_ratio"]
    g = row["bio_growth"]

    if action == "OTP":
        b *= 0.7
    if action == "FACE":
        c *= 0.6
    if action == "OFFLINE":
        b *= 0.8
    if action == "MOBILE":
        g *= 0.5

    new_ciim = 0.5*b + 0.3*g + 0.2*(c*b)
    return new_ciim
