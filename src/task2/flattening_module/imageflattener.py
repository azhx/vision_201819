from tkinter import *
from typing import Tuple, List, Dict
import nPTransform
import numpy as np
from imageprocessor import ImageProcessor, JsonFormatError
import argparse
import os
import json


DOT_SIZE = 10
PANEL_MARKER_COLOUR = 'blue'
CORNER_COLOUR = 'red'
DOT_TAG = 'dots'


class ImageFlattener(ImageProcessor):
    """This class represents an the image processing application
        *** This class assumes the solar panels are rectangles ***

    ==== Properties ===
    dim: This is a tuple containing first the length of the smaller
        edge of the solar panel (width in cm) and then the larger edge
        (height in cm).
    saved: a list of the path to all of the _saved images
    """
    # === Private Attributes ===
    __panels_in: Dict[str, List[Tuple[int, int]]]  # a dictionary whose
    # keys are absolute paths to the images and whose values are a list of pixel
    #  cords of panels in said images.
    __dim: Tuple[int, int]
    __saved: Dict[str, Tuple[int, int]]
    __clicks: List[Tuple[int, int]]  # the clicks
    # that have been made on the canvas since last reload
    __imgs_flattened: bool  # the is the current image a flattened panel
    __num_saved: int  # the number of panels saved during while processing one
    # image

    def __init__(self, master: Tk, panels_in: Dict[str, List[Tuple[int, int]]],
                 save_to: str):
        """
        :param master: The root for this Tk window
        :param panels_in: a dictionary whose keys are absolute paths to the
        images and whose values are a list of pixel cords of panels in
        said images.
        :param save_to: The path to the folder to save images to.
        """
        self.__panels_in = panels_in
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

        ImageProcessor.__init__(self, master, list(panels_in.keys()), save_to)

        self.movable_image.canvas.bind('<Button-1>', self.left_mouse_down)
        self._master.after(200, self.reload)

    @property
    def saved(self) -> Dict[str, Tuple[int, int]]:
        return self.__saved

    @property
    def dim(self) -> Tuple[int, int]:
        return self.__dim

    def left_mouse_down(self, event):
        """Called whenever the left mouse is clicked on the image canvas"""

        if self._img_flattened:
            return

        x, y = self.movable_image.win_to_canvas((event.x, event.y))
        self.movable_image.make_dot(CORNER_COLOUR, (x, y), DOT_SIZE)

        # add tuple (x, y) to existing list
        self.__clicks.append((x, y))

        if len(self.__clicks) >= 4:
            self._img_flattened = True
            self._request_dims()

    def _flatten_img(self):
        """flatten the current img

        Precondition:
        len(self._clicks) == 4
        """
        assert len(self.__clicks) == 4
        # convert clicks to an np array
        rect = np.asarray([np.asarray(
                           np.float32(
                           self.movable_image.canvas_to_cv(p)))
                           for p in self.__clicks])

        flat = nPTransform.four_points_correct_aspect(self.movable_image.cv_img,
                                                      rect,
                                                      self.dim[0],
                                                      self.dim[1])

        self.movable_image.cv_img = flat
        self.movable_image.reset()
        self.movable_image.clear_dots()

        self.__clicks = []

    def _make_panel_dots(self):
        """place dots that mark panels onto screen"""
        for panel_point in self.__panels_in[self.curr_path]:
            self.movable_image.make_dot(PANEL_MARKER_COLOUR,
                                        self.movable_image.cv_to_canvas(panel_point),
                                        DOT_SIZE)

    def reload(self):
        """Overrides because we need to reset img_flattened, add panel markers
        and remove dots"""
        ImageProcessor.reload(self)
        self._img_flattened = False
        self.__clicks = []
        self._make_panel_dots()

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
                    f'_flat_{self.__num_saved}')
            else:
                path = self.save_img_to_folder_with_extra(f'_flat')
            self.__saved[path] = self.dim
            self.__num_saved += 1
            self.reload()

    def _request_dims(self):
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

        if self.dim is not None:
            skip_button = Button(pop, text='Use Last',
                                 command=skip)
            skip_button.pack(side=LEFT)

        pop.mainloop()


def _parse_input(images_input: any) -> Dict[str, List[Tuple[int, int]]]:
    """Attempts to parse input from either list or dictionary if input is
    bad will throw useful errors"""

    panels_in = dict()

    if isinstance(images_input, dict):
        for key in images_input:
            if isinstance(images_input[key], list):
                panels_in[key] = []
                for point in images_input[key]:
                    if isinstance(point, list) \
                       and len(images_input[key]) == 2 \
                       and isinstance(point[0], int) \
                       and isinstance(point[1], int):

                        panels_in[key] = tuple(images_input[key])

                    else:

                        raise JsonFormatError('lists should contain lists of ints\
                                              of len 2')
            else:
                raise JsonFormatError("Json values should be lists")
    elif isinstance(images_input, list):
        for key in images_input:
            panels_in[key] = []
    else:
        raise JsonFormatError('Json should be formatted like a list or dict')

    return panels_in


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Flatten a list of panels')
    parser.add_argument('--input', type=str,
                        help='The path to the jason contain')
    parser.add_argument('--output', type=str,
                        help='The folder to save output json and new images')
    parser.add_argument('--dot_size', type=int,
                        help='The size of the dots used to mark and select panel corners.',
                        default=10
                        )

    arg = parser.parse_args()

    DOT_SIZE = arg.dot_size

    master = Tk()

    with open(arg.input) as input_json:
        images_input = json.load(input_json)

    panels_in = _parse_input(images_input)

    flattener = ImageFlattener(master, panels_in, arg.output)

    master.mainloop()

    if not os.path.exists(arg.output):
        os.makedirs(arg.output)

    with open(os.path.join(arg.output, 'result.json'), 'w') as outfile:
        json.dump(flattener.saved, outfile)
