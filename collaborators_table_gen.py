from json import load, dumps, decoder
from validators import url
from typing import Final, Dict, List
from sys import argv


class CollaboratorTableGen:
    """
    Class for generating an HTML table containing repository collaborator data from JSON and writing to .md file

    Input JSON data format:
        {
            "collaborators": [
                {
                    "name": <(str) names ...>,
                    "page_url": <(str) page-url>,
                    "img_url": <(str) img-url>
                }
            ]
        }

    Requirements:
        pip3 install -r requirements.txt

    Author: Adam Ross
    Date: 05/04/2021
    """

    # CONSTANTS
    FILE_NAME_JSON: Final = 'collaborators.json'  # JSON (.json) file with name matching key for collaborator list data
    FILE_NAME_MD: Final = 'collaborators.md'  # markdown (.md) file the generated table data is written to
    ATTR_NAME: Final = 'name'  # variable used for the collaborator name attribute in the collaborators.json
    ATTR_PAGE_URL: Final = 'page_url'  # variable used for the collaborator page URL attribute in the collaborators.json
    ATTR_IMG_URL: Final = 'img_url'  # variable used for the collaborator image URL attribute in the collaborators.json
    MAX_NUM_COLUMNS: Final = 6  # maximum number of columns in each markdown table row (int)
    IMG_DIMENSIONS: Final = '100'  # height and width of each image in the table, in pixels (str)
    IMG_STYLE: Final = 'border-width:2px;border-style:groove;border-color:gold;border-radius:50%;'  # HTML img style
    TABLE_STYLE: Final = 'border-width:0;text-align:center;'  # HTML table row <tr> and column <td> element style
    ALT_IMG: Final = 'https://avatars.githubusercontent.com/in/15368?s=64&v=4'  # alternative image URL: GitHub logo
    EXCLUSION_LIST: Final = []  # list of names excluded from being in the generated table

    def __init__(self):
        """
        Class constructor:
        - Loads the collaborator data from JSON file and initializes it as a list containing collaborator objects:
            [
                {
                    "name": <(str) names ...>,
                    "page_url": <(str) page-url>,
                    "img_url": <(str) img-url>
                }
            ]
        - Otherwise, if file doesn't exist, initializes an empty list and the following object attributes:
            __name        =   "name"
            __page_url    =   "page_url"
            __img_url     =   "img_url"
        """
        try:
            with open(self.FILE_NAME_JSON) as json_data:
                self.__collaborators_list = load(json_data)[self.FILE_NAME_JSON.split('.')[0]]
            self.__name, self.__page_url, self.__img_url = self.__collaborators_list[0].keys()  # initialize attributes

        except FileNotFoundError:
            self.__collaborators_list = list()  # initialize collaborators list with zero objects
            self.__name, self.__page_url, self.__img_url = self.ATTR_NAME, self.ATTR_PAGE_URL, self.ATTR_IMG_URL

        except decoder.JSONDecodeError as json_err:
            print(json_err.args[0])
            exit(0)  # terminate app if an error occurs in reading data from JSON file

    def __sort_collaborators_list(self) -> None:
        """
        Alphabetically sort the list of table data objects in ascending order, grouped by: surname, forename
        """
        self.__collaborators_list.sort(key=lambda x: (x[self.__name].split(' ')[-1], x[self.__name].split(' ')[0:-1]))

    def __remove_excluded_collaborators(self, collaborators_list_copy) -> List[Dict]:
        """
        Remove all collaborators with a name matching any name in the excluded collaborators list
        :param collaborators_list_copy: copy of the collaborators list for excluding collaborators in the markdown table
        :return: copy of the collaborators list not including the collaborator objects for each excluded collaborator
        """
        return [obj for obj in collaborators_list_copy if obj[self.__name] not in self.EXCLUSION_LIST]

    def save_collaborators_list(self):
        """
        Writes to .json file the alphabetically sorted list of collaborator objects as a value in a dictionary
        """
        self.__sort_collaborators_list()  # alphabetically sort the list

        # write the updated list of collaborator objects as value to the collaborators key in the JSON file
        with open(self.FILE_NAME_JSON, 'w') as output_file:
            output_file.write(dumps({self.FILE_NAME_JSON.split('.')[0]: self.__collaborators_list}, indent=4))

    def add_collaborator(self, names, page_url, img_url) -> None:
        """
        Add a new collaborator as a collaborator object in the collaborators list loaded from the JSON file
        Write the updated collaborators list to the JSON file as a JSON object with 'collaborators' as the key
        :param names: the names of the collaborator; <[forename, ..., surname]> (list[str])
        :param page_url: the URL for the collaborator's linked profile (str)
        :param img_url: the URL for the collaborator's linked image (str)
        """
        assert isinstance(names, list) is True and len(names) >= 1 and url(page_url) is True and url(img_url) is True

        # append the collaborator data as a new object to the list of collaborator objects
        self.__collaborators_list.append(
            {
                self.__name: ' '.join([name.strip().capitalize() for name in names]),
                self.__page_url: page_url.strip(),
                self.__img_url: img_url.strip()
            })

    def generate_table(self) -> None:
        """
        Generate an HTML table containing the list of collaborator objects loaded from the JSON data file
        Write the table to a markdown (.md) file
        """
        assert self.__collaborators_list is not None and len(self.__collaborators_list) > 0

        # remove excluded collaborators from table and set this to a local variable
        collaborators_list = self.__remove_excluded_collaborators(self.__collaborators_list.copy())

        # initiate the HTML table string with a <table> tag
        table_str = '<table>\n'

        # iterate over each collaborator in the collaborators dictionary for appending to the HTML table
        for i in range(len(collaborators_list)):

            # add new row to the markdown table for every number of collaborators matching the num_columns variable
            if i % self.MAX_NUM_COLUMNS == 0:
                table_str += '  <tr style="' + self.TABLE_STYLE + '">\n'

            # add alternative image URL if collaborator is missing an image URL; doesn't have a GitHub account
            if collaborators_list[i][self.__img_url] == '':
                collaborators_list[i][self.__img_url] = self.ALT_IMG

            # add collaborator data to the HTML table - uses deprecated align="center" for GitHub markdown
            table_str += '    <td style="' + self.TABLE_STYLE + '" align="center">' \
                         '<a href="' + collaborators_list[i][self.__page_url] + '" target="_blank">' \
                         '<img src="' + collaborators_list[i][self.__img_url] + '" ' \
                         'width="' + self.IMG_DIMENSIONS + '" ' \
                         'height="' + self.IMG_DIMENSIONS + '" ' \
                         'style="' + self.IMG_STYLE + '" alt=""/><br/>' \
                         '<sub><b>' + collaborators_list[i][self.__name] + '</b></sub></a></td>\n'

            # close row in the HTML table for every number of collaborators matching the num_columns var - 1
            if i % self.MAX_NUM_COLUMNS == self.MAX_NUM_COLUMNS - 1:
                table_str += '  </tr>\n'

        # close last row in the HTML table if the total collaborator count is not divisible by the number of columns
        if len(collaborators_list) % self.MAX_NUM_COLUMNS != 0:
            table_str += '  </tr>\n'

        table_str += '</table>\n'  # close the HTML table

        # add a comment below the table including the total count of collaborators
        table_str += '<!-- collaborator count: ' + str(len(self.__collaborators_list)) + ' -->\n'

        # TODO: convert the HTML5 string to markdown as <img> element style attribute not accepted for GitHub README.md

        # write the table to .md file
        with open(self.FILE_NAME_MD, 'w') as output_file:
            output_file.write(table_str)


if __name__ == '__main__':
    try:
        app = CollaboratorTableGen()

        if len(argv) > 3:
            app.add_collaborator(argv[1:-2], argv[-2], argv[-1])  # accepts arguments: <name, ...> <page-url> <img-url>
            app.save_collaborators_list()
        app.generate_table()

    except AssertionError as ass_err:
        print(ass_err.__class__.__name__)
