"""
This module is the bulk of the algorithm. Usage:
python3 scansion.py input_file_name output_file_name
where input_file_name          is the name of the file that contains the lines
                               to be scanned
      output_file_name         the name of the file to which to print the output

"""

import copy
import math
import random
import sys
import timeit
from utilities import *

# ------------- Global Variables -----------------------------------------------

roots = {}  # dictionary
ALPHA = 1
ELEGIAC = False

# ------------------------------------------------------------------------------
# ------------- The Root Class Definition --------------------------------------
# ------------------------------------------------------------------------------


class Root:
    """This class represents a root."""

    MAX_ROOT_IN_LINE = 5  # the assumed number of maximum occurrences of a root
    # in a single line

    def __init__(self, name):
        """
        The basic constructor.
        :param name: the string representation of the root
        """
        # The line below is for cases like su-a and imposu-it versus
        # svadebit. If su+Consonant is in the root, it is replaced with sva
        self.name = re.sub(r'su([' + VOWELS + '])', r'sv\1', name)
        self.endings = []
        self.groups_p = []

    def __hash__(self):
        """Does exactly what it says"""
        return hash(self.name)

    def __lt__(self, other):
        """Does exactly what it says"""
        return self.name < other.name

    def __gt__(self, other):
        """Does exactly what it says"""
        return other.__lt__(self)

    def add_ending(self, ending, line_index, word_index):
        """
        Adds a possible ending to the root
        :param ending:              the ending as a string
        :param line_index:          line index where this combination occurred
        :param word_index:          word index within the line
        """
        self.endings.append([ending, line_index, word_index, None])

    def ending_prob(self, ending):
        """
        Return the probability of this ending to go with this root.
        :param ending:
        :return: the probability of this ending to be attached to this root,
        the index of the most likely group
        """
        if len(self.groups_p) == 0:
            self.calculate_probabilities()
        if ending == '':
            return self.groups_p[len(ALL)], len(ALL)
        p = 0
        info = ENDINGS[ending]
        max_group = 0
        max_p = 0
        for i in range(len(ALL)):
            if i in info:
                p += self.groups_p[i]
                if self.groups_p[i] > max_p:
                    max_group = i
                    max_p = self.groups_p[i]
        return p, max_group

    def change_meter(self, line_index, word_index, new_metrical_pattern):
        """
        Stores new information about long and short vowels in this root
        :param line_index:           line index where this combination occurred
        :param word_index:           word index within the line
        :param new_metrical_pattern: the encountered metrical pattern
        """
        imin = 0
        imax = len(self.endings)
        while imin <= imax:
            i_avg = int((imin + imax) / 2)
            curr = self.endings[i_avg]
            if (curr[1] == line_index) and (curr[2] == word_index):
                curr[3] = new_metrical_pattern
                break
            elif (curr[1] < line_index) or \
                    ((curr[1] == line_index) and (curr[2] < word_index)):
                imin = i_avg + 1
            else:
                imax = i_avg - 1

    def calculate_probabilities(self):
        """
        The probability of a group is proportional to the number of endings
        that match to this group (each ending is weighted by the number of
        groups is matches to)
        :return:
        """
        self.groups_p = []
        for i in range(len(ALL) + 1):
            self.groups_p.append(0)
        n_matches = 0
        for end in self.endings:
            if end[0] == '':
                self.groups_p[len(ALL)] += 1/ALPHA
                n_matches += 1/ALPHA
            else:
                for group in ENDINGS[end[0]]:
                    self.groups_p[group] += 1/math.log(len(ENDINGS[end[0]]) + 1)
                    n_matches += 1/math.log(len(ENDINGS[end[0]]) + 1)
        for i in range(len(ALL) + 1):
            self.groups_p[i] /= n_matches

    def get_meter(self, ending, exact_match=False):
        """
        Find the most possible combination of long and short vowels in this root
        given the ending that follows it. Use info from the group to which this
        ending most likely belongs to
        :param ending: ending that follows the root in this particular case
        :param exact_match: take into account only instances with the given
        ending
        :return: the list of longs and shorts
        """
        if ending == '':
            exact_match = True
        elif not exact_match:
            mathcing_group = ALL[self.ending_prob(ending)[1]]
        meter = None
        for end in self.endings:
            if (end[0] == ending) or (not exact_match and (end[0] in mathcing_group)):
                if meter is None:
                    meter = end[3]
                else:
                    meter = merge_lists(meter, end[3], True, DUMMY_TOKEN)
                    continue

        return dummy_to_unk(meter)


# ------------------------------------------------------------------------------
# ------------- The Vowel Class Definition -------------------------------------
# ------------------------------------------------------------------------------


class Vowel:
    # these are the three reasons a vowel can be judges short or long
    NOT_DECIDED = 0
    POSITION = 1
    METER = 2
    NATURE = 3

    def __init__(self, vowel, follow):
        """
        The basic constructor. Assigns LONG or UNK value to the vowel based
        on its position
        :param vowel:       the vowel itself
        :param follow:   the set of characters between this vowel and the
                            next one
        :param is_in_the_root: True, if this vowel is part of the root
        """
        self.vowel = vowel
        self.elided = False
        self.longitude = UNK
        self.reason = Vowel.NOT_DECIDED

        if re.match(r'[m]? [h]?$', follow) is not None:
            self.elided = True
            return
        follow = re.sub(r' |' + PSEUDO_CONSONANT, '', follow)
        if (len(self.vowel) > 1) or (len(follow) > 2) or (
                    (len(follow) == 2) and (re.match(SHORT_COMBINATIONS, follow)
                                            is None)) or (
            follow in LONG_CONSONANTS):
            self.longitude = LONG
            self.reason = Vowel.POSITION

    def update(self, new_longitude, new_reason):
        """Update information about the longitude of a vowel"""
        if ((self.reason != self.POSITION) and (self.reason != self.METER)) or (
                    self.longitude == UNK):
            self.reason = new_reason
            self.longitude = new_longitude


# ------------------------------------------------------------------------------
# ------------- The Word Class Definition --------------------------------------
# ------------------------------------------------------------------------------


class Word:
    """Represents a word"""

    def __init__(self, initial_word, line_id, word_id):
        """
        Take a word and first define which of i and u are consonants, when
        gather information about possible roots
        :param initial_word: initial orthography
        :param line_id:      the number of the line in which this word appears
        :param word_id:      the position of this word within the line
        """
        self.initial_orthography = initial_word
        self.word = u_or_v(i_or_j(self.initial_orthography))
        self.root = None  # this will contain the root that was ultimately
        # chosen for this word
        self.vowels = None
        self.line_id = line_id
        self.word_id = word_id
        self.root_length = 0
        self.ending_meter = None

        if self.word not in roots:
            roots[self.word] = Root(self.word)
        roots[self.word].add_ending('', line_id, word_id)
        self.poss_roots = [(roots[self.word], '')]
        for i in range(1, len(self.word)):
            end = self.word[-i:]
            if end in ENDINGS:
                root = self.word[:-i]
                if root not in roots:
                    roots[root] = Root(root)
                roots[root].add_ending(end, line_id, word_id)
                self.poss_roots.append((roots[root], end))

    def form_vowels(self, nextWord):
        """
        Form a list of values for this word after choosing a root
        :param nextWord:
        :return:
        """
        likelihood = -1
        best_group = 0
        total_occurances = 0

        for affix in self.poss_roots:
            total_occurances += len(affix[0].endings)

        for affix in self.poss_roots:
            curr, group = affix[0].ending_prob(affix[1])
            # rounding ensures that probabilities that are equal will still
            # be equal even then calculated differently
            curr = round(curr * len(affix[0].endings)/total_occurances, 3)
            # longest ending 'wins', given equal probabilities
            if curr > likelihood or (curr == likelihood and len(affix[1]) > len(self.root[1])):
                likelihood = curr
                best_group = group
                self.root = affix

        self.vowels = list(re.finditer(SYLLAB, self.root[0].name))
        for i in range(len(self.vowels) - 1):
            letter = self.word[self.vowels[i].start():self.vowels[i].end()]
            follow = self.word[self.vowels[i].end():self.vowels[i + 1].start()]
            self.vowels[i] = Vowel(letter, follow)

        if best_group == len(ALL):
            end = []
        else:
            end = ALL[best_group][self.root[1]]
        self.ending_meter = end
        if self.vowels:
            letter = self.word[self.vowels[-1].start():self.vowels[-1].end()]
            follow = self.root[0].name[self.vowels[-1].end():]
            if not end:
                follow += self.root[1]
                if nextWord is not None:
                    follow += ' ' + list(re.findall(r'^[' + CONSONANTS + ']*', nextWord))[0]
                self.vowels[-1] = Vowel(letter, follow)
                return
            follow += list(re.findall(r'^[' + CONSONANTS + ']*', self.root[1]))[0]
            self.vowels[-1] = Vowel(letter, follow)
            if self.vowels[-1].elided:
                self.root_length = len(self.vowels) - 1
            else:
                self.root_length = len(self.vowels)
        for i in range(len(end) - 1):
            self.vowels.append(Vowel('a',''))  # TODO, a here is not exactly
                                                # correct
        follow = list(re.findall(r'[' + CONSONANTS + ']*$', self.root[1]))[0]
        if nextWord is not None:
            follow += ' ' + list(re.findall(r'^[' + CONSONANTS + ']*', nextWord))[0]
        if len(end) == 0:
            print('Error at line ' + str(self.line_id) +
                  '. Please remove all empty lines from the file. \n' +
                  'Specifics: word = ' + self.initial_orthography + ' end = ' +
                  self.root[1])
        self.vowels.append(Vowel(self.root[1].rstrip(CONSONANTS)[-1], follow))

    def ending_more_info(self):
        """Try to infer teh lengths of endings"""
        for i in range(len(self.ending_meter)):
            self.vowels[len(self.vowels) - len(self.ending_meter) + i].update(
                self.ending_meter[i], Vowel.NATURE)

    def load_meter(self, load_endings=False):
        """Load info from the root and update lengths of the vowels"""
        new_meter = self.root[0].get_meter(self.root[1])
        for i in range(len(new_meter)):
            self.vowels[i].update(new_meter[i], Vowel.NATURE)
        if load_endings:
            self.ending_more_info()

    def update_meter(self, meter):
        for i in range(len(meter)):
            self.vowels[i].update(meter[i], Vowel.METER)
        meter = meter[:self.root_length]
        if self.ending_meter == 0 and self.vowels[-1].reason == Vowel.POSITION:
            # in this case the last vowel is long by position. This information
            # should not be passed to the roots
            self.root[0].change_meter(self.line_id, self.word_id, meter[:-1])
        self.root[0].change_meter(self.line_id, self.word_id, meter)

    def get_meter(self):
        meter = []
        for vowel in self.vowels:
            if not vowel.elided:
                meter.append(vowel.longitude)
        return meter

    def get_length(self):
        """
        Return the number of non elided vowels
        :return:
        """
        length = 0
        for vowel in self.vowels:
            if not vowel.elided:
                length += 1
        return length


# ------------------------------------------------------------------------------
# ------------- The Line Class Definition --------------------------------------
# ------------------------------------------------------------------------------


class Line:
    """This class represents a single line"""
    curr_index = 0  # this is the number of lines initialized. Based on the
    # value of curr_index, each line will be given its own unique index

    def __init__(self, line):
        """
        The basic constructor.
        :param string: the string representation of the line. May contain
                     punctuation signs, vowel u should be typed as "u", not "v",
                     vowel "i" should be typed as "i", not as "j"
        """
        self.scanned = False
        self.index = Line.curr_index
        Line.curr_index += 1

        line = line.lower()
        line = re.sub(r'[^a-z0-9/ ]', ' ', line)  # dealing with punctuation
        line = re.sub(r'[ ]+', ' ', line)
        line = line.rstrip(' ').lstrip(' ')
        line = re.sub(r'([a-z])que( |$)', r'\1 que\2', line)
        # make the ending 'que' into a separate word
        line = re.sub(r'( |^)' + PREFIXES + '([a-z])', r'\1\2w \3', line)
        # make certain perfixes into separate words
        self.initial_orthography = line
        self.line = line.split(' ')
        for i in range(len(self.line)):
            self.line[i] = Word(self.line[i], self.index, i)

    def analyze(self):
        for i in range(len(self.line) - 1):
            self.line[i].form_vowels(self.line[i + 1].word)
        self.line[-1].form_vowels(None)

    def new_trial(self, ending_info=False):
        """
        Tries to do the scansion one more time
        :return:
        """
        if not self.scanned:
            for i in range(len(self.line)):
                self.line[i].load_meter(ending_info)
        return self.get_meter()

    def get_meter(self):
        """
        Return the longitude of all vowels if known as a list
        :return:
        """
        result = []
        for word in self.line:
            result += word.get_meter()
        if not ELEGIAC:
            result[-1] = ANCEPS
        return result

    def update_root_lengths(self, scansion_result):
        """
        Given that the line is scanned in a certain way, update info about roots
        :return:
        """
        if len(scansion_result) <= 1:
            self.scanned = True
            if len(scansion_result) == 0:
                return
        merged_result = scansion_result[0]
        for i in range(1, len(scansion_result)):
            merged_result = merge_lists(merged_result, scansion_result[i], False)
        merged_result[-1] = UNK
        word_begin = 0
        for word in self.line:
            length = word.get_length()
            word.update_meter(merged_result[word_begin:word_begin + length])
            word_begin += length


# ------------- The Main Program -----------------------------------------------


def scansion_versions(line, meter, meterIndex):
    """
    Propose different scansions on a pure logical basis
    :param line: a list where every element represents a syllable. A syllable
                 can either be LONG, SHORT or UNK
    :param meter: meter description
    :param meterIndex: the leftmost part of the meter that can be broken into
                       different parts
    :return: 
    """
    result = []
    for i in range(meterIndex, len(meter)):
        token = meter[i]
        if isinstance(token, list):
            del meter[i]
            for tokenVersion in token:
                meter[i:i] = tokenVersion
                result += scansion_versions(line, meter, i)
                del meter[i:i + len(tokenVersion)]
            meter[i:i] = [token]
            return result
        elif (i >= len(line)) or ((line[i] != meter[i]) and (
                    line[i] != UNK)):
            return result
    if len(meter) == len(line):
        result.append(copy.deepcopy(meter))
    return result


def main(path_to_text, path_to_result, all=True, sectionSize=20, trace=True):
    Line.curr_index = 0
    global roots
    roots = {}
    with open(path_to_text) as file:
        lines = file.readlines()
    if not all:
        begin = random.randint(0, len(lines) - sectionSize)
        if ELEGIAC and begin%2 == 1:
            if begin + sectionSize <= len(lines):
                begin += 1
            else:
                begin -= 1
        lines = lines[begin:begin + sectionSize]
    for i in range(len(lines)):
        lines[i] = Line(lines[i])
    if trace:
        print('Building the dictionary...')
    for i in range(len(lines)):
        lines[i].analyze()
    versions = 0
    run = 0
    change = -1
    while change != 0:
        if change != 0 and trace:
            print('This is run number ' + str(run) + '. Please, wait until the '
                                                   'program terminates...')
        empty = 0
        identified = 0
        newVersion = 0
        for i in range(len(lines)):
            if ELEGIAC and i%2 == 1:
                METER = PENTAMETER
            else:
                METER = HEXAMETER
            if change == -1:
                curr = scansion_versions(lines[i].get_meter(), METER, 0)
            else:
                if run > 1:
                    curr = scansion_versions(lines[i].new_trial(True),
                                                 METER, 0)
                else:
                    curr = scansion_versions(lines[i].new_trial(), METER, 0)
            newVersion += len(curr)
            if len(curr) == 0:
                empty += 1
                curr = scansion_versions(lines[i].get_meter(), METER, 0)
            else:
                if len(curr) == 1:
                    identified += 1
            lines[i].update_root_lengths(curr)
        change = newVersion - versions
        versions = newVersion
        run += 1
        if trace:
            print('\naverage = ' + str(round(versions / len(lines), 4)) +
                ' versions per line.\nidentified = ' +
                str(round(identified / len(lines) * 100, 1)) + '%\nempty = ' +
                str(round(empty / len(lines) * 100, 1)) + '%\n')
    if not all:
        return identified / len(lines)
    if trace:
        print('Printing the results...')
    with open(path_to_result, 'w') as file:
        for i in range(len(lines)):
            curr = scansion_versions(lines[i].get_meter(), HEXAMETER, 0)
            to_print = ''
            j = 0
            if not curr:
                curr = [lines[i].get_meter()]
                curr[0][-1] = '?'
            while j < len(curr):
                for char in curr[j]:
                    to_print += char
                if j < len(curr) - 1:
                    to_print += '|'
                j += 1
            file.write(to_print + '\n')


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: %s input_file_name output_file_name"
              % sys.argv[0])
        sys.exit(-1)
    main(sys.argv[1], sys.argv[2])
    # main('input/aeneid.txt', 'output/dict.txt', 'output/scanned.txt')
    """ls = [2, 4, 8, 10, 20, 25, 30, 35, 40, 50, 100, 300, 500, 2000]
    result = []
    for l in ls:
        # result.append(timeit.timeit(lambda: main('input/aeneid.txt', 'output/dict.txt', 'output/scanned.txt', False, l), number=50))
        result.append(0)
        for i in range(int(ls[-1]/l)):
            result[-1] += (main('input/tristia.txt', 'output/dict.txt', 'output/scanned.txt', False, l))
        result[-1] /= ls[-1]/l
    print(result)"""
