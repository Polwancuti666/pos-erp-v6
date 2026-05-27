from pos_erp.beauty_ui import BeautyDashboardTheme, render_dashboard_html


def test_beauty_dashboard_theme_uses_cute_premium_palette():
    theme = BeautyDashboardTheme()
    assert theme.primary == "#ff6fae"
    assert theme.background == "#fff7fb"
    assert theme.accent == "#b76cff"
    assert theme.radius_px == 24


def test_render_dashboard_html_contains_beauty_wellbeing_visual_language():
    html = render_dashboard_html(branch_name="Beauty Wellbeing HQ")
    assert "Beauty Wellbeing HQ" in html
    assert "POS-ERP Beauty Dashboard" in html
    assert "#ff6fae" in html
    assert "border-radius: 24px" in html
    assert "cute-premium" in html
