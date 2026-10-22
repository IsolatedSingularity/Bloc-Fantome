"""Shared authored contact/phrase times for the temporary Pass B performance."""
SKULL_CONTACTS = (25.45, 26.55, 27.65)
CONTACT_EVENTS = (
    (1.0, 'foot', .30), (2.0, 'foot', .34), (3.0, 'foot', .32),
    (4.0, 'foot', .39), (5.0, 'foot', .36), (6.0, 'foot', .40),
    (6.7, 'grip', .36), (8.7, 'grip', .42), (20.5, 'fall', .68),
    *((t, 'skull', gain) for t, gain in zip(SKULL_CONTACTS, (.55, .62, .72))),
    (32.6, 'collapse', .56), (35.4, 'collapse', .44),
)
# Deliberate silence between unlike phrases; never a ten-voice wall or a loop.
VOCAL_EVENTS = (
    (3.3, 'voice11', .22), (7.2, 'voice01', .36), (10.8, 'voice06', .30),
    (14.0, 'voice03', .34), (17.4, 'voice02', .42), (20.8, 'voice08', .32),
    (23.1, 'voice05', .40), (25.45, 'voice10', .34), (28.2, 'voice04', .43),
    (31.6, 'voice07', .38), (36.3, 'voice09', .30),
)
