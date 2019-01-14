from src.utilities import *

replace = {' ⁔': '\n', '⁔ ': '\n', '⁔': '\n', ' ': '\n',
           'ā': 'a_', 'ă': 'a^', 'Ā': 'A_', 'Ă': 'A^',
           'ē': 'e_', 'ĕ': 'e^', 'Ē': 'E_', 'Ĕ': 'E^',
           'ī': 'i_', 'ĭ': 'i^', 'Ĭ': 'I^', 'Ī': 'I_',
           'ŏ': 'o^', 'ō': 'o_', 'Ŏ': 'O^', 'Ō': 'O_',
           'ū': 'u_', 'ŭ': 'u^', 'V̄': 'U_', 'V̆': 'U^',
           'ȳ': 'y_', 'y̆': 'y^',
           'ǣ': '[ae]', 'Ǣ': '[Ae]', 'æ': '[ae]',
           'œ̄́': '[Oe]', 'œ̄': '[oe]',
           'œ': '[oe]', 'Œ̄': '[Oe]'}

embellishments = {replace[x]: x for x in replace.keys()}

input = "I_o_nja I_o^ni^a"
print(multireplace(input, embellishments))