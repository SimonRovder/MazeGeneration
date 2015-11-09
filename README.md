# Maze Generation Algorithm
_This repository contains an algorithm for creating arbitrarily large mazes_



## Usage
Clone the repository, navigate to it and run _mazegen.py_ using this command:

```python mazegen.py my_maze 3200 3200 1024 4```

You will get the general idea.



The program splits the requested area into small tiles, saving their definitions and relative locations within the _arch.json_ file. The same structure is mimicked by the _maze.html_ file, where the actual tiles are embedded. The tiles themselves are stored in the _Submazes_ folder.

The tiles are generated in parallel in as many threads as the user specifies in the command line argument. Upon the completion of a tile, the program creates a _.done_ file, which goes with it. The reason for these files is that if the program is forcefully terminated, it can always be restarted with the same command line arguments and it will continue where it left off. Note that the _arch.json_ file must be present in order for it to really continue where it left off. If this file is not present, the program will create a new file, potentially overwriting all previous work.

Once the maze generation is complete, open _maze.html_ to view the whole thing. Your browser may not display all the tiles at the same time, as this would require significant amounts of memory, but rest assured, they are there.

I used this algorithm to generate a 1 000 000 by 1 000 000 pixel maze on Google Compute Engine, worked perfectly fine.