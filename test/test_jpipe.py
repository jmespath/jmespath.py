import io
import os
import sys
import tempfile
import unittest.mock

try:
    import jpipe
except ImportError:
    sys.path.append(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib"
        )
    )
    import jpipe


class JPipeTest(unittest.TestCase):
    def testJPipe(self):
        for input_args, input_json, input_expr, expected_output, expected_retval in (
            ((), """{"hello": "world"}""", "@", '{\n  "hello": "world"\n}\n', 0),
            ((), """{"hello": "world"}""", "@.hello", '"world"\n', 0),
            (("-u",), """{"hello": "world"}""", "@.hello", "world\n", 0),
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
                retval = jpipe.jpipe_main(
                    [
                        "jpipe",
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
