# jpipe

A python implementation (using
[jmespath.py](https://github.com/jmespath/jmespath.py))
of the [`jp` CLI](https://github.com/jmespath/jp) for the
[JMESPath](https://jmespath.org/) language (a query language for JSON).

## Compatiblity

The aim is for 100% compatiblity with the official
[`jp` CLI for JMESPath](https://github.com/jmespath/jp).
Please open an issue if an incompatibility is found.

## Usage
```
usage: jpipe [-h] [-e EXPR_FILE] [-f FILENAME] [-u] [--ast] [expression]

  jpipe - A python implementation of the jp cli for JMESPath

positional arguments:
  expression

optional arguments:
  -h, --help            show this help message and exit
  -e EXPR_FILE, --expr-file EXPR_FILE
                        Read JMESPath expression from the specified file.
  -f FILENAME, --filename FILENAME
                        The filename containing the input data. If a filename
                        is not given then data is read from stdin.
  -u, --unquoted        If the final result is a string, it will be printed
                        without quotes.
  --ast                 Only print the AST of the parsed expression. Do not
                        rely on this output, only useful for debugging
                        purposes.
```
