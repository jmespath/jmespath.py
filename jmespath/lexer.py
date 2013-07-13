import re

class LexerDefinition(object):
    reflags = re.DOTALL
    reserved = {}
    tokens = (
        'STAR',
        'DOT',
        'LBRACKET',
        'RBRACKET',
        'OR',
        'NUMBER',
        'IDENTIFIER',
    ) + tuple(reserved.values())

    t_STAR = r'\*'
    t_DOT = r'\.'
    t_LBRACKET = r'\['
    t_RBRACKET = r'\]'
    t_OR = r'\|\|'
    t_ignore = ' '

    _requires_escape = [chr(i) for i in range(0x20, 0x2f + 1)] + \
        [chr(i) for i in range(0x3a, 0x40 + 1)] + \
        [chr(i) for i in range(0x5b, 0x5e + 1)] + \
        [chr(0x60)] + \
        [chr(i) for i in range(0x7b, 0x7e + 1)]
    _can_be_escaped = {
        'b': '\b', 'n': '\n', 'f': '\f', 'r': '\r', 't': '\t', '\\': '\\',
    }
    _escape_chars_str = ''.join(
        [hex(ord(i)).replace('0x', r'\x') for i in
         _requires_escape + list(_can_be_escaped.keys())])

    def t_NUMBER(self, t):
        r'-?\d+'
        t.value = int(t.value)
        return t

    def t_IDENTIFIER(self, t):
        t.type = self.reserved.get(t.value, 'IDENTIFIER')
        i = 0
        if t.value[0] == '"' and t.value[-1] == '"':
            t.value = t.value[1:-1]
            if '\\"' in t.value:
                t.value = t.value.replace('\\"', '"')
            return t
        if '\\' not in t.value:
            # If there's no '\' in the string, we don't have
            # to do any additional (slower) processing.
            return t
        chunks = []
        while True:
            next_index = t.value.find('\\', i)
            if next_index == -1:
                chunks.append(t.value[i:])
                break
            else:
                replace_char = self._can_be_escaped.get(
                    t.value[next_index + 1])
                if replace_char is not None:
                    chunks.append(t.value[i:next_index])
                    chunks.append(replace_char)
                else:
                    # Otherwise we just remove the '\' char entirely,
                    # so something like '\.' becomes '.'.
                    chunks.append(t.value[i:next_index])
                    chunks.append(t.value[next_index + 1])
                i = next_index + 2
        t.value = ''.join(chunks)
        return t

    t_IDENTIFIER.__doc__ = (r'((([0-9A-Z_a-z])|(\\[%s]))+)|("(\"|.)*")'
                            % _escape_chars_str)

    def t_error(self, t):
        raise ValueError("Illegal token value '%s'" % t.value)
