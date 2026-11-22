"""The overlay panels: where a click goes, and the hover tips (which wait for the mouse to rest)."""
from tests.test_rendering import _frames


def _rest(app, pos):
    """Puts the mouse at `pos` and lets it rest long enough for the tips to show, then draws a frame."""
    overlay = app.overlay
    overlay.hover(*pos)
    overlay.ctx.mouse_since -= 5
    _frames(app)


def test_clicks_reach_the_toolbar_and_panels(make_app):
    app = make_app()
    _frames(app, 3)
    overlay = app.overlay
    rect, action, *_ = overlay.toolbar.buttons[0]
    assert overlay.click(*rect.center) == (True, action)           # A button gives its action
    bar = overlay.toolbar.bar_rect
    assert overlay.click(bar.right - 1, bar.y + 1) in ((True, None), (True, action))   # The bar swallows the click
    assert overlay.click(*app.screen.layout.world.center) == (False, None)   # The world is left to the selection

    app.do("help")
    _frames(app)
    assert overlay.any_modal() and overlay.click(5, 5) == (True, None)   # The help closes on any click
    assert not overlay.help.open

    app.do("legend")
    _frames(app)
    assert overlay.legend.rect is not None and overlay.blocks(*overlay.legend.rect.center)
    assert overlay.click(*overlay.legend.rect.center) == (True, None)    # On the legend: not a click in the world
    app.do("legend")
    _frames(app)
    assert overlay.legend.rect is None                                  # Hidden panel: no rect, no click


def test_settings_panel_clicks(make_app):
    app = make_app()
    app.do("params_panel")
    _frames(app)
    params = app.overlay.params
    assert app.overlay.any_modal() and params.rect is not None
    rect, action = params._hits[0]
    assert app.overlay.click(*rect.center) == (True, action)
    assert app.overlay.click(1, 1) == (True, None) and not params.open   # Outside the panel: closes


def test_large_network_is_movable_by_its_title(make_app):
    app = make_app()
    _frames(app)                                                         # The layout exists once a frame ran
    app.do("best")
    app.do("graph")
    app.do("graph")
    _frames(app, 3)
    net = app.overlay.net
    assert net.big and net.rect is not None
    assert not net.grab(net.rect.x + 5, net.rect.bottom - 5)            # Only the title grabs
    assert net.grab(net.rect.x + 5, net.rect.y + 5)
    net.hover(10, 10)                                                    # No button pressed: the drag ends
    assert net._drag is None


def test_hover_tips(make_app):
    app = make_app()
    app.do("best")
    _frames(app, 3)
    overlay, layout = app.overlay, app.screen.layout
    rect = overlay.toolbar.buttons[0][0]
    _rest(app, rect.center)                                              # A tool bar button
    _rest(app, overlay.toolbar.speed_rect.center)                        # The speed label
    sb = layout.sidebar
    for slot in app.hud.slots.values():                                  # Every card of the side bar
        _rest(app, (sb.x + slot.centerx, sb.y + slot.centery))
    vw, vh = app.scene.size                                              # The camera follows the best creature:
    _rest(app, (layout.world.x + vw // 2, layout.world.y + vh // 2))     # it is at the centre of the world
    app.do("params_panel")
    _rest(app, rect.center)                                              # Modal panel open: no tip, no crash
