import os, sys

if sys.platform == "linux" and hasattr(sys, "_MEIPASS"):
    gst_plugin_path = os.path.join(sys._MEIPASS, "gst-plugins")
    if os.path.isdir(gst_plugin_path):
        os.environ["GST_PLUGIN_PATH_1_0"] = gst_plugin_path
        os.environ["GST_PLUGIN_SYSTEM_PATH_1_0"] = gst_plugin_path
        # Disable the plugin scanner — all plugins are already in our bundle
        os.environ["GST_PLUGIN_SCANNER_1_0"] = ""
        # Prevent GStreamer from writing a registry cache into the user's home
        os.environ["GST_REGISTRY"] = os.path.join(sys._MEIPASS, ".gst-registry")
