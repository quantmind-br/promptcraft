package apperror

import "testing"

func TestErrorCarriesMessageAndCode(t *testing.T) {
	cases := []struct {
		err     *Error
		message string
		code    string
	}{
		{CommandNotFoundError("not found"), "not found", CodeCommandNotFound},
		{TemplateReadError("read failed", CodeTemplatePermission), "read failed", CodeTemplatePermission},
		{TemplateReadError("read failed", ""), "read failed", CodeTemplateReadError},
		{TemplateError("empty"), "empty", "TEMPLATE_ERROR"},
		{ConfigurationError("bad config"), "bad config", "CONFIGURATION_ERROR"},
		{New("plain", "CUSTOM"), "plain", "CUSTOM"},
	}

	for _, testCase := range cases {
		if testCase.err.Error() != testCase.message {
			t.Fatalf("message mismatch: %q", testCase.err.Error())
		}
		if testCase.err.Code() != testCase.code {
			t.Fatalf("code mismatch: got %q want %q", testCase.err.Code(), testCase.code)
		}
	}
}
