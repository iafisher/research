import enum
import random
from dataclasses import dataclass


# dimensions for Google Slides with 18-pt Roboto Mono typeface
GOOGLE_SLIDES_WIDTH = 65
GOOGLE_SLIDES_HEIGHT = 18


class Alignment(enum.Enum):
    LEFT = "left"
    CENTER = "center"


@dataclass
class Layout:
    # how many background lines between content lines?
    vertical_space_between: int
    # how many background columns between staggered content lines?
    # requires staggered == True
    horizontal_space_between: int
    # how many spaces before and after content per line?
    horizontal_padding: int
    # how many spaces above and below content lines?
    vertical_padding: int
    # fill in corners?
    # requires vertical_padding >= 1
    corners: bool
    # stagger content lines horizontally?
    staggered: bool
    # how to align content lines?
    horizontal_alignment: Alignment
    # how many background columns between left edge and first content line?
    # requires horizontal_alignment == Alignment.LEFT
    absolute_left_padding: int

    @classmethod
    def title(cls):
        return cls(
            vertical_space_between=0,
            horizontal_space_between=1,
            # horizontal_padding=2,
            horizontal_padding=1,
            # vertical_padding=1,
            vertical_padding=0,
            corners=True,
            staggered=True,
            horizontal_alignment=Alignment.CENTER,
            absolute_left_padding=0,
        )


def n_random_bits(n):
    return "".join(n_random_bits_list(n))


def n_random_bits_list(n):
    return [str(random.randint(0, 1)) for _ in range(n)]


def random_line():
    return n_random_bits(GOOGLE_SLIDES_WIDTH)


def random_text_line(text, offset):
    return (
        n_random_bits(offset)
        + text
        + n_random_bits(GOOGLE_SLIDES_WIDTH - offset - len(text))
    )


def n_random_lines(n):
    return " ".join(random_line() for _ in range(n))


def random_slide():
    return n_random_lines(GOOGLE_SLIDES_HEIGHT)


def random_text_slide(lines, layout):
    content_lines = _lay_out_content(lines, layout)
    lines_before, lines_after = _split_number(GOOGLE_SLIDES_HEIGHT - len(content_lines))

    r = [random_line() for _ in range(lines_before)]
    r.extend(content_lines)
    r.extend([random_line() for _ in range(lines_after)])
    assert len(r) == GOOGLE_SLIDES_HEIGHT
    return " ".join(r)


def _lay_out_content(lines, layout):
    space_required = 0
    for line in lines:
        space_required += (layout.horizontal_padding * 2) + len(line)

    space_required += (len(lines) - 1) * layout.horizontal_space_between
    assert space_required <= GOOGLE_SLIDES_WIDTH, "lines too long"
    spaces_before, spaces_after = _split_number(GOOGLE_SLIDES_WIDTH - space_required)

    if layout.horizontal_alignment == Alignment.CENTER:
        offset = spaces_before
    else:
        offset = layout.absolute_left_padding

    r = []
    for line in lines:
        each_line_length = (layout.horizontal_padding * 2) + len(line)

        r.extend(
            _lay_out_vertical_padding(
                layout, line_length=each_line_length, offset=offset
            )
        )

        b2 = n_random_bits(offset)
        b2 += " " * layout.horizontal_padding
        b2 += line
        b2 += " " * layout.horizontal_padding
        b2 += n_random_bits(GOOGLE_SLIDES_WIDTH - len(b2))
        r.append(b2)

        r.extend(
            _lay_out_vertical_padding(
                layout, line_length=each_line_length, offset=offset
            )
        )

        if layout.staggered:
            offset += each_line_length + layout.horizontal_space_between

        for _ in range(layout.vertical_space_between):
            r.append(random_line())

    return r


def _lay_out_vertical_padding(layout, *, line_length, offset):
    blank_spaces = " " * line_length

    if layout.corners:
        blank_spaces_corners = " " * (line_length - 2)
    else:
        blank_spaces_corners = blank_spaces

    r = []
    if layout.vertical_padding > 0:
        r.append(random_text_line(blank_spaces_corners, offset + 1))
        for _ in range(layout.vertical_padding - 1):
            r.append(random_text_line(blank_spaces, offset))

    return r


def _split_number(n):
    a = n // 2
    b = n - a
    return a, b


class Lines:
    def __init__(self, *lines, stagger=0):
        self.lines = lines
        self.stagger = stagger

    def to_lines(self):
        if self.stagger:
            r = []
            offset = 0
            for line in self.lines:
                r.append(("\0" * offset) + line)
                offset += len(line) + self.stagger
            return r
        else:
            return self.lines[:]


class SlideBuilder:
    def __init__(self, *, height=GOOGLE_SLIDES_HEIGHT, width=GOOGLE_SLIDES_WIDTH):
        self.height = height
        self.width = width
        self.content_by_line = [[] for _ in range(self.height)]

    def place(self, element, *, h, v):
        element_lines = element if isinstance(element, list) else [element]
        h = self._normalize_h(h, element_lines)
        v = self._normalize_v(v, element_lines)

        v_offset = v
        for line in element_lines:
            self.content_by_line[v_offset].append((h, line))
            v_offset += 1

        return self

    def _normalize_h(self, h, element_lines):
        if h == "center":
            width = max(map(len, element_lines))
            h, _ = _split_number(self.width - width)
        else:
            assert isinstance(h, int)
            if h < 0:
                h = self.width + (h - 1)

        return h

    def _normalize_v(self, v, element_lines):
        if v == "center":
            height = len(element_lines)
            v, _ = _split_number(self.height - height)
        else:
            assert isinstance(v, int)
            if v < 0:
                v = self.height + (v - 1)

        return v

    def build(self):
        r = [n_random_bits_list(self.width) for _ in range(self.height)]
        for lineno, content_list in enumerate(self.content_by_line):
            for offset, content in content_list:
                self._paste_content(r[lineno], offset, content)

        return " ".join("".join(l) for l in r)

    def _paste_content(self, buffer, offset, content):
        for i in range(len(content)):
            if content[i] == "\0":
                continue

            buffer[offset + i] = content[i]


def stagger(sb, *lines, h, v, gap=1):
    r = []
    offset = 0
    for line in lines:
        r.append(("\0" * offset) + line)
        offset += len(line) + gap
    sb.place(r, h=h, v=v)


sb = SlideBuilder()
stagger(sb, " HACKER ", " NEWS ", " POETRY ", h="center", v="center")
sb.place(" iafisher, jul 2024 ", h=3, v=-1)
print(sb.build())
print()
