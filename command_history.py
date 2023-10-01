bl_info = {
    "name": "Console command history",
    "blender": (2, 80, 0),
    "category": "Development",
    "description": "Console command history cached between sessions",
    "author": "Hannes D",
    "version": (1, 0),
}


import bpy
import console_python
from bpy.app.handlers import persistent


__original_add_scrollback = console_python.add_scrollback


# Define a preference property to store whether to load history
class PersistentConsoleHistoryPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    prev_session_commands: bpy.props.StringProperty(
        name="Command String",
        description="Command String",
    )  # the most recent command strings are saved at the back

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("console.restore_history", text="Restore Console History")
        row = layout.row()
        row.prop(self, "prev_session_commands", text="Command String")


def overwrite_add_scrollback_method():
    """
    overwrite the default scrollback to track the console commands
    """
    def add_scrollback(text, text_type):
        for line in text.split("\n"):
            bpy.ops.console.scrollback_append(text=line, type=text_type)

        save_command_history()  # todo save every time we run a command is a bit overkill
        # bpy.context.preferences.addons[__name__].preferences.prev_session_commands = text
        print("add_scrollback", text, text_type)
        # return console_python.add_scrollback(text, text_type)
    console_python.add_scrollback = add_scrollback


def restore_add_scrollback_method():
    console_python.add_scrollback = __original_add_scrollback


class RestoreConsoleHistoryOperator(bpy.types.Operator):
    bl_idname = "console.restore_history"
    bl_label = "Restore previous session Console History"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Add commands from persistent history to console history
        command = bpy.context.preferences.addons[__name__].preferences.prev_session_commands

        save_command_history()

        from bpy import context
        window = context.window_manager.windows[0]
        screen = window.screen
        for area in screen.areas:
            if area.type == 'CONSOLE':
                with context.temp_override(window=window, area=area):
                    for line in command.split("\n"):
                        bpy.ops.console.history_append(text=line)
                    break

        return {'FINISHED'}


def save_command_history():
    # get original value in copy buffer
    original_clipboard = bpy.context.window_manager.clipboard
    # copy the command history to the clipboard

    from bpy import context
    window = context.window_manager.windows[0]
    screen = window.screen
    for area in screen.areas:
        if area.type == 'CONSOLE':
            with context.temp_override(window=window, area=area):
                bpy.ops.console.copy_as_script()
                break

    # get the command history from the clipboard
    command_history_raw = bpy.context.window_manager.clipboard
    # split by new line, and remove all line not starting with #
    new_lines = [line for line in command_history_raw.split("\n") if not line.startswith("#")]
    old_lines = bpy.context.preferences.addons[__name__].preferences.prev_session_commands.split("\n")
    command_lines = new_lines + old_lines
    # remove dupe lines, but keep order
    command_lines = list(dict.fromkeys(command_lines))  # todo keep order of commands
    command_history = "\n".join(command_lines)
    # restore the original value in the copy buffer
    bpy.context.window_manager.clipboard = original_clipboard
    bpy.context.preferences.addons[__name__].preferences.prev_session_commands = command_history
    print("SAVED COMMAND HISTORY")

@persistent
def handler_restore_history(dummy):
    bpy.ops.console.restore_history()

def register():
    bpy.utils.register_class(RestoreConsoleHistoryOperator)
    bpy.utils.register_class(PersistentConsoleHistoryPreferences)
    overwrite_add_scrollback_method()
    bpy.app.handlers.load_post.append(handler_restore_history)


def unregister():
    bpy.utils.unregister_class(RestoreConsoleHistoryOperator)
    bpy.utils.unregister_class(PersistentConsoleHistoryPreferences)
    restore_add_scrollback_method()
    bpy.app.handlers.load_post.remove(handler_restore_history)
