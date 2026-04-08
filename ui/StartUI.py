import imgui
import glfw
import OpenGL.GL as gl
from imgui.integrations.glfw import GlfwRenderer
from collections import deque

from ui.SimulationManager import SimulationManager
from ui.ConfigPanel import ConfigPanel
from ui.ChartPanel import ChartPanel
from ui.OrderBookPanel import OrderBookPanel
from ui.StatsPanel import StatsPanel
from ui.MarketAnalysisPanel import MarketAnalysisPanel


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

    _, titleBarHeight, _, _ = glfw.get_window_frame_size(window)
    glfw.set_window_pos(window, 0, titleBarHeight)
    glfw.make_context_current(window)
    glfw.swap_interval(1)

    gl.glClearColor(0.15, 0.15, 0.15, 1.0)

    imgui.create_context()
    io = imgui.get_io()

    renderer = GlfwRenderer(window)
    io.display_size = 1920, 1080

    dataQueue = deque(maxlen=8)
    orderBookQueue = deque(maxlen=2048)
    simManager = SimulationManager(dataQueue, orderBookQueue)

    chartPanel = ChartPanel(dataQueue)
    orderbookPanel = OrderBookPanel(simManager, orderBookQueue)
    statsPanel = StatsPanel(simManager)
    marketPanel = MarketAnalysisPanel(simManager)
    configPanel = ConfigPanel(simManager, chartPanel, statsPanel, marketPanel, orderbookPanel)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        renderer.process_inputs()

        width, height = glfw.get_window_size(window)
        io.display_size = width, height

        imgui.new_frame()

        configPanel.render()
        chartPanel.render()
        orderbookPanel.render()
        statsPanel.render()
        marketPanel.render()

        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        renderer.render(imgui.get_draw_data())
        glfw.swap_buffers(window)

    simManager.stopSimulation()
    renderer.shutdown()
    glfw.terminate()

if __name__ == "__main__":
    main()