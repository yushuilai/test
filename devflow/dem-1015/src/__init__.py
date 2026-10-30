"""Login page behavioural core (Python implementation).

The tech-feel web login page is modelled here as pure Python so every acceptance
criterion in the req_spec can be exercised deterministically by pytest without a
browser. Browser-only metrics (LCP/CLS/FPS/axe) are covered by declared targets
and logic proxies; a real browser run remains part of the manual acceptance.
"""
