from . import camera_viewer

def register():
    camera_viewer.register()

def unregister():
    camera_viewer.unregister()

if __name__ == "__main__":
    register()