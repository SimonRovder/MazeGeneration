""" Algorithm for creating arbitrarily large mazes.
    Copyright (c) 2015 Simon Rovder """

from random          import randint
from math            import ceil
from multiprocessing import Pool
import json
import sys
import os

# ------------------------------------------------------------------------------------
# - The following constants are necessary for building the monochromatic bitmap file -
# ------------------------------------------------------------------------------------


CONSTANT_SEQUENCE   = bytearray([66, 71, 82, 115, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 0, 0, 0, 0, 0])
DATA_OFFSET         = 130
INFO_HEADER_SIZE    = bytearray([108, 0, 0, 0])
SIGNATURE           = bytearray([66, 77])
PLANES              = bytearray([1, 0])
BITCOUNT            = bytearray([1, 0])
ZEROS               = bytearray([0, 0, 0, 0])
COLOURS             = bytearray([2, 0, 0, 0])
PER_METER_CONSTANTS = bytearray([19, 11, 0, 0])


# Command line argument defined values:
SECTOR_DIMS         = 1024
PROCESS_COUNT       = 1
WIDTH               = 32
HEIGHT              = 32


def architect(x1, y1, x2, y2, ht=False, hl=False, wr=True, wb=True):
    """
    The recursive architect method designs the tile layout of the maze. Parameters x1, x2, y1 and y2 define the
    area that is to be split into tiles. The parameters of this method along with a file name define a full
    schema of a sub maze tile.

    Note that this method does not actually build any real maze yet. It only pre-processes the required size and breaks the maze down
    into tiles.

    :param ht: True if there is to be an exit from this tile to the one above it.
    :param hl: True if there is to be an exit from this tile to the one on the left of it.
    :param wr: True if there are no further tiles on the right of this tile.
    :param wb: True if there are no further tiles below this tile.
    :return: The tile layout and tile definitions.
    """

    width  = x2-x1
    height = y2-y1

    if width < SECTOR_DIMS and height < SECTOR_DIMS:
        # If the width and height of this tile is acceptable, return the schema.
        return dict(x1=x1, x2=x2, y1=y1, y2=y2, ht=ht, hl=hl, wr=wr, wb=wb, file_name="(%s_%s)_(%s_%s)" % (x1, y1, x2, y2))

    # If this tile is too big, split it into two smaller tiles, depending on whether the height if greater
    # than the width or the other way around.

    if width > height:
        split = randint(x1/32 + 1, x2/32 - 1)*32
        return dict(
            left=architect(x1=x1, y1=y1, x2=split-1, y2=y2, ht=(ht and (2*split > x1+x2)), hl=hl, wr=False, wb=wb),
            right=architect(x1=split, y1=y1, x2=x2, y2=y2, ht=(ht and (2*split <= x1+x2)), hl=True, wr=wr, wb=wb)
        )
    else:
        split = randint(y1/32 + 1, y2/32 - 1)*32
        return dict(
            top=architect(x1=x1, y1=y1, x2=x2, y2=split-1, ht=ht, hl=(hl and (2*split > y1+y2)), wr=wr, wb=False),
            bottom=architect(x1=x1, y1=split, x2=x2, y2=y2, ht=True, hl=(hl and (2*split <= y1+y2)), wr=wr, wb=wb)
        )


class Maze(object):

    """
    The Maze object is basically a blank bit canvas that can be painted on. Its width and height must be multiples
    of 32. It implements a method for dumping the byte array into a byte file and into a monochromatic bitmap file.

    Filling in bits and clearing them is done using bit masks and bitwise OR and AND.
    """

    _masks_or  = bytearray([128, 64, 32, 16, 8, 4, 2, 1])
    _masks_and = bytearray([255-int(bb) for bb in _masks_or])

    def __init__(self, width, height):
        """ Create a blank canvas. """

        assert(width  % 32 == 0)
        assert(height % 32 == 0)

        self.a_width = width/8
        self.maze    = bytearray(self.a_width*height)
        self.width   = width
        self.height  = height

    def fill(self, x, y):
        """ Fill in the bit at position x;y using bitwise OR """
        self.maze[self.a_width*y+x/8] |= self._masks_or[x % 8]

    def empty(self, x, y):
        """ Clear in the bit at position x;y using bitwise AND """
        self.maze[self.a_width*y+x/8] &= self._masks_and[x % 8]

    def write_byte_file(self, path):
        """ Dump bytes into a file """
        open(path, 'wb').write(self.maze)

    def write_bmp_file(self, path):
        """ Dump the canvas into a monochromatic bitmap file. """
        image_size = int(ceil(self.width/32)*4)*self.height
        file_size  = image_size + DATA_OFFSET
        with open(path, 'wb') as f:
            f.write(SIGNATURE)
            f.write(to_byte_array(file_size, 3))
            f.write(ZEROS)
            f.write(to_byte_array(DATA_OFFSET, 3))
            f.write(INFO_HEADER_SIZE)
            f.write(to_byte_array(self.width, 3))
            f.write(to_byte_array(self.height, 3))
            f.write(PLANES)
            f.write(BITCOUNT)
            f.write(ZEROS)
            f.write(to_byte_array(image_size, 3))
            f.write(PER_METER_CONSTANTS)
            f.write(PER_METER_CONSTANTS)
            f.write(COLOURS)
            f.write(COLOURS)
            f.write(CONSTANT_SEQUENCE)
            while self.maze:
                f.write(self.maze[-self.width/8:])
                del self.maze[-self.width/8:]


def to_byte_array(number, factor):
    """
    Method turns a number into its byte representation in a byte array of size 'factors' + 1
    For example:
    >>> to_byte_array(7,1)
    >>> [7, 0]
    >>> to_byte_array(256,1)
    >>> [0, 1]
    >>> to_byte_array(258,2)
    >>> [2, 1, 0]
    """
    if factor == 0:
        return bytearray([number])
    return to_byte_array(number % (256**factor), factor-1) + bytearray([number/(256**factor)])


def sub_maze_gen(x1, x2, y1, y2, ht, hl, wr, wb, file_name, bmp, directory):
    """
    Method creates an empty maze tile, which is defined by the parameters x1, x2, y1, y2, ht, hl, wr, wb, file_name.

    It generates the main structure defined in the parameters and then calls the recursive_generation function,
    which covers the inner area of the tile.

    :param bmp: Dumps as a bitmap file if True, as raw bytes if false.
    :param directory: Specifies the directory to which the file is to be dumped.
    """

    r_x2 = x2-x1
    r_y2 = y2-y1

    # Create blank canvas
    maze_obj = Maze(width=r_x2+1, height=r_y2+1)
    y = 0
    x = 0

    # Create wall on the left
    while y <= r_y2:
        maze_obj.fill(x=0, y=y)
        y += 1

    # Create wall on the top
    while x <= r_x2:
        maze_obj.fill(x=x, y=0)
        x += 1

    # Create the wall on the right if needed
    if wr:
        y = 0
        while y <= r_y2:
            maze_obj.fill(x=r_x2, y=y)
            maze_obj.fill(x=r_x2-1, y=y)
            y += 1
        r_x2 -= 2

    # Create the wall on the bottom if needed
    if wb:
        x = 0
        while x <= r_x2:
            maze_obj.fill(x=x, y=r_y2)
            maze_obj.fill(x=x, y=r_y2-1)
            x += 1
        r_y2 -= 2

    # Create a hole in the top wall if needed
    if ht:
        x = randint(0, (x2-x1)/2-1)*2 + 1
        maze_obj.empty(x=x, y=0)

    # Create a hole in the left wall if needed
    if hl:
        y = randint(0, (y2-y1)/2-1)*2 + 1
        maze_obj.empty(x=0, y=y)

    # Recursively generate the internal walls within the tile
    recursive_generation(maze_obj=maze_obj, x1=1, x2=r_x2, y1=1, y2=r_y2)

    # dump the file
    if bmp:
        maze_obj.write_bmp_file(os.path.join(directory, 'Submazes', file_name + '.bmp'))
    else:
        maze_obj.write_byte_file(os.path.join(directory, 'Submazes', file_name))

    # Create a .done file. (Everything is done by this point)
    open(os.path.join(directory, 'Submazes', file_name + '.done'), 'w').write('DONE')


def recursive_generation(maze_obj, x1, y1, x2, y2):
    """
    Basic recursive wall generating algorithm. Cuts the area defined by x1, y1, x2, y2 into two rooms by a wall,
    creates a hole in the wall and proceeds to call itself on the two rooms. Repeated until one of the dimensions
    is 1.
    """
    if x2-x1 <= 1 or y2-y1 <= 1:
        return
    if x2-x1 < y2-y1:
        y = randint(y1/2+1, y2/2)*2
        for x in xrange(x1, x2+1):
            maze_obj.fill(x=x, y=y)
        hole = randint(x1/2, x2/2)*2 + 1
        maze_obj.empty(x=hole, y=y)
        recursive_generation(maze_obj, x1=x1, y1=y1,  x2=x2, y2=y-1)
        recursive_generation(maze_obj, x1=x1, y1=y+1, x2=x2, y2=y2)

    else:
        x = randint(x1/2 + 1, x2/2)*2
        for y in xrange(y1, y2+1):
            maze_obj.fill(x=x, y=y)
        hole = randint(y1/2, y2/2)*2 + 1
        maze_obj.empty(x=x, y=hole)
        recursive_generation(maze_obj, x1=x1,  y1=y1, x2=x-1, y2=y2)
        recursive_generation(maze_obj, x1=x+1, y1=y1, x2=x2,  y2=y2)


def extract_tile_plans(jdata):
    """ Recursive method. Extracts the individual maze parameters form the architect file in a single
        list, disregarding the relative positions and structure. """

    if 'top' in jdata:
        return extract_tile_plans(jdata['top']) + extract_tile_plans(jdata['bottom'])
    if 'left' in jdata:
        return extract_tile_plans(jdata['left']) + extract_tile_plans(jdata['right'])
    return [jdata]


def process_executor(plans_data):
    """ Iterates over the tile plans and creates the tiles one by one, informing on its progress. """
    done  = 0
    plans = plans_data['plans']
    for plan in plans:
        sub_maze_gen(plan['x1'], plan['x2'], plan['y1'], plan['y2'], plan['ht'], plan['hl'], plan['wr'], plan['wb'], plan['file_name'], True, plans_data['directory'])
        done += (plan['x2'] - plan['x1'] + 1)*(plan['y2'] - plan['y1'] + 1)
        print "Process %d at %.2f percent." % (plans_data['process_number'], done * 100.0 / plans_data['area'])


def submaze_generator(directory):
    """
    Method gets a list of tile plans and evenly distributes them among as many processes as
    defined in the command line argument. It then runs the generation of these lists in parallel.
    """

    # Extract individual tile plans
    plans = extract_tile_plans(json.loads(open(os.path.join(directory, 'arch.json')).read())['plans'])

    # Prepare the data to be fed into the processes
    processes = [dict(plans=list(), area=0, directory=directory, process_number=i) for i in xrange(PROCESS_COUNT)]

    # Evenly spread out the tile plans among the processes
    for plan in plans:

        # Check whether the .done file already exists. If so, skip the tile plan. (Already generated)
        if not os.path.isfile(os.path.join(directory, 'Submazes', plan['file_name']) + '.done'):
            # Find the process that covers the smallest amount of tile area
            smallest = 0
            for i, process in enumerate(processes):
                if process['area'] < processes[smallest]['area']:
                    smallest = i

            # Add the current tile plan to the smallest process
            processes[smallest]['plans'].append(plan)
            # Increment the total area covered by that process
            processes[smallest]['area'] += (plan['x2'] - plan['x1'] + 1)*(plan['y2'] - plan['y1'] + 1)

    # Create a multiprocessing pool and map the process_executor function onto the list of processes.
    pool = Pool(processes=PROCESS_COUNT)
    pool.map(process_executor, processes)
    pool.close()
    pool.join()


def create_html_page(arch):
    """
    Recursive method creates the BODY of a HTML page such that when viewed in a browser, the
    page correctly stitches the sub maze tiles together.
    :param arch: The tile architecture file.
    """
    if 'top' in arch:
        first_width,  first_height,  first_html  = create_html_page(arch['top'])
        second_width, second_height, second_html = create_html_page(arch['bottom'])
        return first_width, first_height + second_height, '<TABLE><TR><TD>%s</TD></TR><TR><TD>%s</TD></TR></TABLE>' % (first_html, second_html)
    if 'left' in arch:
        first_width,  first_height,  first_html  = create_html_page(arch['left'])
        second_width, second_height, second_html = create_html_page(arch['right'])
        return first_width + second_width, first_height, '<TABLE><TR><TD>%s</TD><TD>%s</TD></TR></TABLE>' % (first_html, second_html)
    return arch['x2'] - arch['x1'] + 1, arch['y2'] - arch['y1'] + 1, '<IMG src="Submazes/%s.bmp" style="float:left;width:%spx;height:%spx;"/>' % (arch['file_name'], arch['x2'] - arch['x1'] + 1,arch['y2'] - arch['y1'] + 1)


if __name__ == '__main__':

    arguments_are_valid = True
    try:
        directory     = sys.argv[1]
        WIDTH         = int(sys.argv[2])
        HEIGHT        = int(sys.argv[3])
        SECTOR_DIMS   = int(sys.argv[4])
        PROCESS_COUNT = int(sys.argv[5])
        assert(WIDTH % 32 == 0)
        assert(HEIGHT % 32 == 0)
        assert(SECTOR_DIMS % 32 == 0)
        assert(SECTOR_DIMS < 32767)
        assert(32 < SECTOR_DIMS)
        assert(all([x > 0 for x in (WIDTH, HEIGHT, SECTOR_DIMS, PROCESS_COUNT)]))
    except:
        print "\n\nArguments are incorrect! Usage: \n\nmaze.py <directory> <width> <height> <sector_size> <processes>" \
              "\n\nWhere:\n" \
              "directory   - The directory where all the maze data will be saved.\n" \
              "width       - The width of the resulting maze ( must be a multiple of 32 )\n" \
              "height      - The height of the resulting maze ( must be a multiple of 32 )\n" \
              "sector_size - The maximum length of any side of a sub maze ( must be a multiple of 32, must be greater than 32 and must be less than 32767 )\n" \
              "processes   - The number of parallel threads you wish the generator to use\n\n"
        arguments_are_valid = False

    if arguments_are_valid:
        if not os.path.exists(directory):
            os.makedirs(directory)
        if not os.path.exists(os.path.join(directory, "Submazes")):
            os.makedirs(os.path.join(directory, "Submazes"))

        if not os.path.isfile(os.path.join(directory, 'arch.json')):
            open(os.path.join(directory, 'styles.css'), 'w').write(open('styles.css', 'r').read())

            print "Creating architect file"
            arch = architect(0, 0, WIDTH-1, HEIGHT-1)
            open(os.path.join(directory, 'arch.json'), 'w').write(json.dumps({'width': WIDTH, 'height': HEIGHT, 'plans': arch}, indent=4))

            print "Creating html page"
            width, height, html = create_html_page(arch)
            open(os.path.join(directory, 'maze.html'), 'w').write("<HTML><link rel='stylesheet' type='text/css' href='styles.css'><BODY>" + html + "</BODY></HTML>")

        print "Generating mazes"
        submaze_generator(directory)
