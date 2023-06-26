import puz
import requests

from .basedownloader import BaseDownloader
from ..util import unidecode

class NewYorkTimesSyndicatedDownloader(BaseDownloader):
    command = 'nyts'
    outlet = 'New York Times(Syndicated)'
    outlet_prefix = 'NY Times(Syndicated)'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.url_format = 'https://nytsyn.pzzl.com/nytsyn-crossword-mh/nytsyncrossword?date={}'

    # @staticmethod
    # def matches_url(url_components):
    #     return ('nytsyn.pzzl.com' in url_components.netloc
    #                 and 'nytsyn-crossword-mh/nytsyncrossword' in url_components.path)

    def find_latest(self):
        return 'https://nytsyn.pzzl.com/nytsyn-crossword-mh/nytsyncrossword'

    def find_by_date(self, dt):
        #earliest possible 2008-06-02
        return self.url_format.format(dt.strftime('%y%m%d'))

    def find_solver(self, url):
        return url
    
    def fetch_data(self, solver_url):
        res = requests.get(solver_url)

        xword_data = res.text
        return xword_data
    
    def parse_xword(self, xword_data, enumeration=True):
        lines = xword_data.splitlines()        
        puzzle = puz.Puzzle()
        puzzle.title = lines[4]
        if lines[6].startswith("<NOTEPAD>"):
            end_of_notes = lines[6].index('</NOTEPAD>')
            puzzle.notes = lines[6][9:end_of_notes]
            puzzle.author = lines[6][end_of_notes+10:]
        else:
            puzzle.author = lines[6]
        puzzle.width = int(lines[8])
        puzzle.height = int(lines[10])
        num_clues_across = int(lines[12])
        num_clues_down = int(lines[14])

        raw_grid = ''.join(lines[16:16+puzzle.height])
        clues_across = lines[16+puzzle.height+1:16+puzzle.height+1+num_clues_across]
        clues_down = lines[16+puzzle.height+1+num_clues_across+1:16+puzzle.height+1+num_clues_across+1+num_clues_down]

        fill = ''
        markup = b''
        grid = [['' for i in range(puzzle.width)] for j in range(puzzle.height)]
        
        for y in range(puzzle.height):
            for x in range(puzzle.width):
                if raw_grid[0] == '%':      #circled cells
                    markup += b'\x80'
                    raw_grid = raw_grid[1:]
                elif raw_grid[0] == '^':    #shaded cells
                    markup += b'\x80'       #treat as circled cells
                    raw_grid = raw_grid[1:]
                else:
                    markup += b'\x00'

                if raw_grid[0] == '#' or raw_grid[0] == '.':
                    grid[y][x] = '.'
                    fill += '.'
                elif raw_grid[0].isalpha():
                    grid[y][x] = raw_grid[0]
                    fill += '-'
                raw_grid = raw_grid[1:]

                #rebus
                while raw_grid and raw_grid[0] == ',':
                    grid[y][x] += raw_grid[1]
                    raw_grid = raw_grid[2:]
        
        solution = ''.join([cell[0] for row in grid for cell in row])

        rebus_board = []
        rebus_index = 0
        rebus_table = ''

        clues = []
        for y in range(puzzle.height):
            for x in range(puzzle.width):
                if grid[y][x] == '.':
                    rebus_board.append(0)
                    continue
                if len(grid[y][x]) > 1:
                    rebus_board.append(rebus_index + 1)
                    rebus_table += '{:2d}:{};'.format(rebus_index, grid[y][x])
                    rebus_index += 1
                else:
                    rebus_board.append(0)

                if ((x == 0 or grid[y][x-1] == '.') and
                    (x + 1 < puzzle.width and grid[y][x+1] != '.')):
                    clues.append(clues_across[0])
                    clues_across = clues_across[1:]
                
                if ((y == 0 or grid[y-1][x] == '.') and
                    (y + 1 < puzzle.height and grid[y+1][x] != '.')):
                    clues.append(clues_down[0])
                    clues_down = clues_down[1:]
        
        if b'\x80' in markup:
            puzzle.extensions[b'GEXT'] = markup
            puzzle._extensions_order.append(b'GEXT')
            puzzle.markup()
        
        if any(rebus_board):
            puzzle.extensions[b'GRBS'] = bytes(rebus_board)
            puzzle.extensions[b'RTBL'] = rebus_table.encode(puz.ENCODING)
            puzzle._extensions_order.extend([b'GRBS', b'RTBL'])
            puzzle.rebus()

        puzzle.solution = solution
        puzzle.fill = fill
        puzzle.clues = clues

        return puzzle

    def pick_filename(self, puzzle, **kwargs):
        split_on_dashes = puzzle.title.split(' - ')
        if len(split_on_dashes) > 1:
            title = split_on_dashes[-1].strip()
        else:
            title = ''

        return super().pick_filename(puzzle, title=title, **kwargs)