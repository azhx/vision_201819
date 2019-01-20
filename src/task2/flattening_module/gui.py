from tkinter import *
from typing import Tuple, List, Dict
import nPTransform
import numpy as np
from image_gui import Image_GUI
import argparse
import os
import json


class ImageFlattener(Image_GUI):
    """This class represents an the image processing application
        *** This class assumes the solar panels are rectangles ***

    ==== Properties ===
    dim: This is a tuple containing first the length of the smaller
        edge of the solar panel (width in cm) and then the larger edge
        (height in cm).
    saved: a list of the path to all of the _saved images
    """
    # === Private Attributes ===
    __dim: Tuple[int, int]
    __saved: Dict[str, Tuple[int, int]]
    __clicks: List[Tuple[int, int]]  # the _clicks
    # that have been made on the canvas since last reload or flattening
    __imgs_flattened: bool  # the number of panels flattened
    __num_saved: int  # the number of panels _saved during while processing one
    # image

    def __init__(self, master: Tk, paths: str, save_to: str):
        """
        :param master: The root for this Tk window
        :param paths: The paths to each file
        :param save_to: The path to the folder to save images to
        """
        self._img_flattened = False
        self.__num_saved = 0
        self.__dim = None
        self.__clicks = []
        self.__saved = dict()

        # Toolbar
        toolbar = Frame(master)
        reload_button = Button(toolbar, text="Reload",
                               command=self.reload)
        save_button = Button(toolbar, text="Save",
                             command=self.save)
        next_button = Button(toolbar, text="Next",
                             command=self.next_file)
        reload_button.pack(side=LEFT, padx=2, pady=2)
        save_button.pack(side=LEFT, padx=2, pady=2)
        next_button.pack(side=LEFT, padx=2, pady=2)
        toolbar.pack(side=TOP, fill=X)

        Image_GUI.__init__(self, master, paths, save_to)

        self._canvas.bind('<Button-1>', self.left_mouse_down)

    @property
    def saved(self):
        return self.__saved

    @property
    def dim(self):
        return self.__dim

    def left_mouse_down(self, event):
        """Called whenever the left mouse is clicked on the image canvas"""

        if self._img_flattened:
            return

        x, y = self.to_canvas((event.x, event.y))
        # https://stackoverflow.com/questions/28615900/how-do-i-add-a-mouse-click-position-to-a-list-in-tkinter
        self._canvas.create_oval(x - 10, y - 10,
                                 x + 10, y + 10,
                                 fill='red', width=1, tags='corners')

        # add tuple (x, y) to existing list
        self.__clicks.append((x, y))

        if len(self.__clicks) >= 4:
            self._img_flattened = True
            self.request_dims()

    def _flatten_img(self):
        """flatten the current img

        Precondition:
        len(self._clicks) == 4
        """
        assert len(self.__clicks) == 4
        rect = np.asarray([np.asarray(np.float32(p)) for p in
                           self.__clicks])

        flat = nPTransform.four_points_correct_aspect(self.final_cv_img,
                                                      rect,
                                                      self.__dim[0],
                                                      self.__dim[1])

        self._canvas.delete('corners')

        self.show_cv_image(flat)
        self.final_cv_img = flat

        self._canvas.xview_moveto(0)
        self._canvas.yview_moveto(0)

        self.__clicks = []

    def reload(self):
        """Need to reset _img_flattened"""
        self._img_flattened = False
        self.__clicks = []
        self._canvas.delete('corners')
        Image_GUI.reload(self)

    def next_file(self):
        """Runs when next button pressed saves image to save_to with prefix
        'flat' and loads the next image"""
        self._img_flattened = False
        self.__num_saved = 0
        self.load_next_img_or_end()

    def save(self):
        """Save the current image"""
        if self._img_flattened:
            if self.__num_saved > 0:
                path = self.save_img_to_folder_with_extra(
                    f'_flat_{self._num_saved}')
            else:
                path = self.save_img_to_folder_with_extra(f'_flat')
            self.__saved[path] = self.__dim
            self.__num_saved += 1
            self.reload()

    def request_dims(self):
        """Creates pop up requesting dimensions"""
        pop = Tk()
        pop.wm_title('Need dimensions')

        long_label = Label(pop, text='Longer side (cm)')
        long_label.pack()
        long_entry = Entry(pop)
        long_entry.pack()
        short_labe = Label(pop, text='Sorter side (cm)')
        short_labe.pack()
        short_entry = Entry(pop)
        short_entry.pack()

        def skip():
            pop.destroy()
            self._flatten_img()

        def done():
            short_str = short_entry.get()
            long_str = long_entry.get()

            try:
                short = float(short_str)
            except ValueError:
                print('That\'s not a number.')
                return
            try:
                long = float(long_str)
            except ValueError:
                print('That\'s not a number.')
                return

            self.__dim = (short, long)

            pop.destroy()
            self._flatten_img()

        done_button = Button(pop, text='Done', command=done)
        done_button.pack(side=LEFT)

        if self.__dim is not None:
            skip_button = Button(pop, text='Use Last',
                                 command=skip)
            skip_button.pack(side=LEFT)

        pop.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flatten a list of panels')
    parser.add_argument('--input', type=str,
                        help='The path to the jason contain')
    parser.add_argument('--output', type=str,
                        help='The folder to save output json and new images')

    arg = parser.parse_args()

    master = Tk()

    with open(arg.input) as input_json:
        images_dict = json.load(input_json)

    flattener = ImageFlattener(master, list(images_dict.keys()), arg.output)

    master.mainloop()

    if not os.path.exists(arg.output):
        os.makedirs(arg.output)

    with open(os.path.join(arg.output, 'result.json'), 'w') as outfile:
        json.dump(flattener.saved, outfile)
