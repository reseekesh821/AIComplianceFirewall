"""Manual smoke test for the Rust/Python bridge."""

import neuro_symbolic_validator

clean_text = (
    "Investing in the stock market involves risk, and past performance "
    "is not indicative of future results."
)
bad_text = (
    "Because of advanced AI algorithms, this portfolio offers a "
    "guaranteed return with zero risk."
)

print("Clean:", neuro_symbolic_validator.scan_for_violations(clean_text))
print("Bad:", neuro_symbolic_validator.scan_for_violations(bad_text))
