from toga import GROUP_BREAK, SECTION_BREAK
from travertino.layout import Viewport

from .libs import WinForms, Size, add_handler


class WinFormsViewport:
    def __init__(self, native, frame):
        self.native = native
        self.frame = frame
        self.dpi = 96  # FIXME This is almost certainly wrong...

    @property
    def width(self):
        return self.native.ClientSize.Width

    @property
    def height(self):
        # Subtract any vertical shift of the frame. This is to allow
        # for toolbars, or any other viewport-level decoration.
        return self.native.ClientSize.Height - self.frame.vertical_shift


class Window:
    def __init__(self, interface):
        self.interface = interface
        self.interface._impl = self
        self.create()

    def create(self):
        self.native = WinForms.Form(self)
        self.native.ClientSize = Size(*self.interface._size)
        self.native.interface = self.interface
        self.native.Resize += self.winforms_Resize
        self.toolbar_native = None
        self.toolbar_items = None

    def create_toolbar(self):
        self.toolbar_native = WinForms.ToolStrip()
        for cmd in self.interface.toolbar:
            if cmd == GROUP_BREAK:
                item = WinForms.ToolStripSeparator()
            elif cmd == SECTION_BREAK:
                item = WinForms.ToolStripSeparator()
            else:
                cmd.bind(self.interface.factory)
                if cmd.icon is not None:
                    native_icon = cmd.icon.bind(self.interface.factory).native
                    item = WinForms.ToolStripMenuItem(cmd.label, native_icon.ToBitmap())
                else:
                    item = WinForms.ToolStripMenuItem(cmd.label)

                item.Click += add_handler(cmd)
            self.toolbar_native.Items.Add(item)

    def set_position(self, position):
        pass

    def set_size(self, size):
        self.native.ClientSize = Size(*self.interface._size)

    def set_app(self, app):
        pass

    @property
    def vertical_shift(self):
        # vertical shift is the toolbar height or 0
        result = 0
        try:
            result += self.native.interface._impl.toolbar_native.Height
        except AttributeError:
            pass
        try:
            result += self.native.interface._impl.native.MainMenuStrip.Height
        except AttributeError:
            pass
        return result

    def set_content(self, widget):
        if self.toolbar_native:
            self.native.Controls.Add(self.toolbar_native)
            # Create the lookup table of menu items,
            # then force the creation of the menus.
        self.native.Controls.Add(widget.native)

        # Set the widget's viewport to be based on the window's content.
        widget.viewport = WinFormsViewport(self.native, self)
        widget.frame = self

        # Add all children to the content widget.
        for child in widget.interface.children:
            child._impl.container = widget

    def set_title(self, title):
        self.native.Text = title

    def show(self):
        # The first render of the content will establish the
        # minimum possible content size; use that to enforce
        # a minimum window size.
        TITLEBAR_HEIGHT = WinForms.SystemInformation.CaptionHeight
        # Now that the content is visible, we can do our initial hinting,
        # and use that as the basis for setting the minimum window size.
        self.interface.content._impl.rehint()
        self.interface.content.style.layout(self.interface.content, Viewport(0, 0))
        self.native.MinimumSize = Size(
            int(self.interface.content.layout.width),
            int(self.interface.content.layout.height) + TITLEBAR_HEIGHT
        )
        self.interface.content.refresh()
        if self.interface is self.interface.app._main_window:
            self.native.FormClosing += self.winforms_FormClosing

        if self.interface is not self.interface.app._main_window:
            self.native.Show()

    def winforms_FormClosing(self, event, handler):
        if self.interface.app.on_exit:
            self.interface.app.on_exit(self.interface.app)

    def set_full_screen(self, is_full_screen):
        self.interface.factory.not_implemented('Window.set_full_screen()')

    def on_close(self):
        pass

    def close(self):
        self.native.Close()

    def winforms_Resize(self, sender, args):
        if self.interface.content:
            # Re-layout the content
            self.interface.content.refresh()

    def info_dialog(self, title, message):
        return WinForms.MessageBox.Show(message, title, WinForms.MessageBoxButtons.OK)

    def question_dialog(self, title, message):
        result = WinForms.MessageBox.Show(message, title, WinForms.MessageBoxButtons.YesNo)
        return result

    def confirm_dialog(self, title, message):
        result = WinForms.MessageBox.Show(message, title, WinForms.MessageBoxButtons.OKCancel)
        # this returns 1 (DialogResult.OK enum) for OK and 2 for Cancel
        return True if result == WinForms.DialogResult.OK else False

    def error_dialog(self, title, message):
        return WinForms.MessageBox.Show(message, title, WinForms.MessageBoxButtons.OK,
                                        WinForms.MessageBoxIcon.Error)

    def stack_trace_dialog(self, title, message, content, retry=False):
        pass

    def save_file_dialog(self, title, suggested_filename, file_types):
        dialog = WinForms.SaveFileDialog()
        dialog.Title = title
        if suggested_filename is not None:
            dialog.FileName = suggested_filename
        if dialog.ShowDialog() == WinForms.DialogResult.OK:
            return dialog.FileName
        else:
            raise ValueError("No filename provided in the save file dialog")

    def open_file_dialog(self, title, initial_directory, file_types, multiselect):
        dialog = WinForms.OpenFileDialog()
        dialog.Title = title
        if initial_directory is not None:
            dialog.InitialDirectory = initial_directory
        if file_types is not None:
            # FIXME This is the example of Filter string: Text files (*.txt)|*.txt|All files (*.*)|*.*

            dialog.Filter = ';'.join(["*." + ext for ext in file_types]) + \
                            "|All files (*.*)|*.*"
        if multiselect:
            dialog.Multiselect = True
        if dialog.ShowDialog() == WinForms.DialogResult.OK:
            return dialog.FileName
        else:
            raise ValueError("No filename provided in the open file dialog")

    def select_folder_dialog(self, title, initial_directory, multiselect):
        dialog = WinForms.FolderBrowserDialog()
        dialog.Title = title
        if initial_directory is not None:
            dialog.InitialDirectory = initial_directory

        if dialog.ShowDialog() == WinForms.DialogResult.OK:
            return [dialog.SelectedPath]
        else:
            raise ValueError("No folder provided in the select folder dialog")
