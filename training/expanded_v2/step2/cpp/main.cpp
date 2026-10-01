#include <iostream>
#include CANDIDATE
int main() {
    for (int64_t value : {0, -12, 120}) {
        // A fresh process per variant prevents OpenFHE context-cache state leaking
        // from the configured example into the missing-feature example.
        std::cout << "{\"case\":\"" << CASE_NAME << "\",\"input\":" << value;
        try {
            auto result = roundtrip(value);
            std::cout << ",\"value\":" << result;
        } catch (const std::exception& error) {
            std::cerr << error.what() << '\n';
            std::cout << ",\"error_type\":\"exception\"";
        }
        std::cout << "}\n";
    }
}
