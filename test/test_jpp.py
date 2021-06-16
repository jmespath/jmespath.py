import io
import os
import sys
import tempfile
import unittest.mock

try:
    import jpipe.jpp.main
except ImportError:
    sys.path.append(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib"
        )
    )
    import jpipe.jpp.main


class JPPTest(unittest.TestCase):
    def testJPP(self):
        for input_args, input_json, input_expr, expected_output, expected_retval in (
            ((), """{"hello": "world"}""", "@", '{\n  "hello": "world"\n}\n', 0),
            (("-c",), """{"hello": "world"}""", "@", '{"hello":"world"}\n', 0),
            (("-c",), """{\n  "foo": "bar"\n}{   \n"foo": "x"\n}""", "@", '{"foo":"bar"}\n{"foo":"x"}\n', 0),
            (("-a", "-c",), """{"foo": ["a"]}{"foo": ["a", "x"]}""", "@", '{"foo":["a","x"]}\n', 0),
            (("-a", "-c",), """{"foo": ["a"]}{"foo": ["a"]}""", "@", '{"foo":["a"]}\n', 0),
            (("-a", "-c",), """{"foo": ["a", "a"]}{"foo": ["a"]}""", "@", '{"foo":["a","a"]}\n', 0),
            (("-a", "-c",), """{"foo": ["a", "a"]}{"foo": ["a", "b"]}""", "@", '{"foo":["a","a","b"]}\n', 0),
            (("-a", "-c",), """["a"]["x"]""", "@", '["a","x"]\n', 0),
            (("-c", "-s",), """"a"\n"x"\n""", "@", '["a","x"]\n', 0),
            ((), """{"hello": "world"}""", "@.hello", '"world"\n', 0),
            (("-u",), """{"hello": "world"}""", "@.hello", "world\n", 0),
            (("-R", "-a", "-c",), "hello world", "@", '"hello world"\n', 0),
            (("-R", "-r",), "hello world\n", "@", 'hello world\n', 0),
            (("-R", "-u",), "hello world\n", "@", 'hello world\n', 0),
            (("-R", "-c",), "line 1\nline 2\nline 3\n", "@", '"line 1\\n"\n"line 2\\n"\n"line 3\\n"\n', 0),
            (("-R", "-s", "-c",), "line 1\nline 2\nline 3\n", "@", '"line 1\\nline 2\\nline 3\\n"\n', 0),
        ):
            self._test_inputs(
                input_args, input_json, input_expr, expected_output, expected_retval
            )

    def _test_inputs(
        self, input_args, input_json, input_expr, expected_output, expected_retval
    ):
        with tempfile.NamedTemporaryFile(
            mode="wt"
        ) as expr_file, tempfile.NamedTemporaryFile(mode="wt") as filename:

            expr_file.write(input_expr)
            expr_file.flush()

            filename.write(input_json)
            filename.flush()

            mock_stdout = io.StringIO()
            with unittest.mock.patch("sys.stdout", new=mock_stdout):
                retval = jpipe.jpp.main.jpp_main(
                    [
                        "jpp",
                        "--expr-file",
                        expr_file.name,
                        "--filename",
                        filename.name,
                    ]
                    + list(input_args)
                )
            self.assertEqual(retval, expected_retval)
            self.assertEqual(mock_stdout.getvalue(), expected_output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
