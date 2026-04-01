import imgui
import glfw
import OpenGL.GL as gl
from imgui.integrations.glfw import GlfwRenderer
from queue import Queue

from simulation_manager import SimulationManager
from config_panel import ConfigPanel
from chart_panel import ChartPanel
from orderbook_panel import OrderBookPanel
from stats_panel import StatsPanel
from market_analysis_panel import MarketAnalysisPanel


def main():
    if not glfw.init():
        print("GLFW init failed")
        return

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 2)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)

    window = glfw.create_window(1920, 1080, "Simulator UI", None, None)
    if not window:
        print("Window creation failed")
        glfw.terminate()
        return

    _, title_bar_height, _, _ = glfw.get_window_frame_size(window)
    glfw.set_window_pos(window, 0, title_bar_height)
    glfw.make_context_current(window)
    glfw.swap_interval(1)

    gl.glClearColor(0.15, 0.15, 0.15, 1.0)

    imgui.create_context()
    io = imgui.get_io()

    renderer = GlfwRenderer(window)
    io.display_size = 1920, 1080

    # Shared state
    data_queue = Queue(maxsize=8)
    order_book_queue = Queue(maxsize=2048)
    sim_manager = SimulationManager(data_queue, order_book_queue)

    chart_panel = ChartPanel(data_queue)
    orderbook_panel = OrderBookPanel(sim_manager, order_book_queue)
    stats_panel = StatsPanel(sim_manager)
    market_panel = MarketAnalysisPanel(sim_manager)
    config_panel = ConfigPanel(sim_manager, chart_panel, stats_panel, market_panel, orderbook_panel)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        renderer.process_inputs()

        width, height = glfw.get_window_size(window)
        io.display_size = width, height

        imgui.new_frame()

        config_panel.render()
        chart_panel.render()
        orderbook_panel.render()
        stats_panel.render()
        market_panel.render()

        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    sim_manager.stop_simulation()
    renderer.shutdown()
    glfw.terminate()

if __name__ == "__main__":
    main()