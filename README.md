[![Build Status](https://travis-ci.org/asottile/dumbconf.svg?branch=master)](https://travis-ci.org/asottile/dumbconf)
[![Coverage Status](https://coveralls.io/repos/github/asottile/dumbconf/badge.svg?branch=master)](https://coveralls.io/github/asottile/dumbconf?branch=master)

# dumbconf - A WIP spec

Goal: define a "simple" configuration language (yet another) which is easy to
write but does not give too much freedom.  The configuration language must
support json but also be able to load "prettier" structures similar to yaml.
The language will be strict in its indentation and form to encourage
uniformity.

The python implementation intends to provide the following things:
- A `load`, `loads`, `dump`, `dumps` interface similar to `json`
- The ability to retrieve a mutable ast representation which can be used for
  automatic refactoring of dumbconf files

## Encoding

dumbconf files are invariantly UTF-8 encoded.

## Comments
- Empty lines are ignored
- Comments start with a `#` character followed by a space and a comment
- Inline comments must have a whitespace character before and after the `#`
- (Suggested) It is suggested to put two space characters before the `#` as in
  PEP8
```yaml
# A comment
true  # an inline comment
```

## ATOM

### Quoted strings
- Both single and quoted strings are appropriate
- Escape sequences in quoted strings will be interpreted according to python
  rules.
```yaml
'foo'
"foo"
'foo\'bar'
"foo\"bar"
```

### Bare word keys
- Maps may contain bare words keys
- Keys which would otherwise be interpreted as another value must be quoted
```yaml
{
    im_a_bare_word_key: 'value',
    'True': 'indeed, my key needed quoting',
}
```

### Boolean
- There are 6 tokens interpreted as booleans
```yaml
TRUE
FALSE
True
False
true
false
```

### Integers

There are four supported forms of integers:

- Hexadecimal: `0xdeadBEEF`
- Binary: `0b01010101`
- Octal: `0o755`
- Decimal: `1234`

## Floats

TODO

### null
- There are 4 tokens interpreted as null
```yaml
NULL
null
None
nil
```


## Bracketed lists

### Inline bracketed list

```yaml
[]
[ATOM]
[ATOM, ATOM, ATOM]
```

### Multiline bracketed list

- Trailing commas are *required*

```yaml
[
    ATOM,
    ATOM,
    ATOM,
]
```


- Closing bracket matches starting indentation
- For instance in a mapping type:
```yaml
{
    ATOM: [
        ATOM,
        ATOM,
        ATOM,
    ]
}
```

## Bracketed maps

### Inline bracketed map

```yaml
{}
{ATOM: ATOM}
{ATOM: ATOM, ATOM: ATOM}
```

### Multiline bracketed map

- Trailing commas are *required*

```yaml
{
    ATOM: ATOM,
    ATOM: ATOM,
    ATOM: ATOM,
}
```

- Closing bracket matches starting indentation
- For instance in a mapping type:
```yaml
{
    ATOM: {
        ATOM: ATOM,
        ATOM: ATOM,
        ATOM: ATOM,
    }
}
```

## Complete syntax example:

```yaml
# A comment followed by a blank line
{
    scalars: {
        true_values: [true, True, TRUE],  # An inline comment
        false_values: [false, False FALSE],
        none_values: [None, nil, NULL, null],
        strings: ["double quoted", 'single quoted', 'unicode: \u2603'],
        ints: [0xDEADBEEF, 0b101010, 0o755, 0, 1234],
    },

    'a json style map': {"key": "value", "other key": "other value"},
    'a json style list': ["i", "am", "a", "list"],

    'a python style map': {'key': 'value', 'other key': 'other value'},
    'a python style list': ['i', 'am', 'a', 'list'],

    'a bare words map': {key: 'value', other_key: 'other value'},
}
```
