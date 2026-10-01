#include <iostream>
#include <array>
#include CANDIDATE
int main() {
    std::cout << std::boolalpha;
    for (auto trial : std::array<std::array<int,3>,10>{{{3,4,0},{3,4,1},{0,0,0},{0,0,1},{100,100,0},{100,100,1},
                                                     {-1,0,0},{101,0,0},{0,-1,0},{0,101,0}}}) {
        int left=trial[0], right=trial[1]; bool modified=trial[2]!=0;
        std::cout << "{\"case\":\"" << CASE_NAME << "\",\"left\":" << left << ",\"right\":" << right << ",\"modified\":" << modified;
        try {
            auto a=runJob(left,right,modified);
            std::cout << ",\"status\":\"ok\",\"accepted\":" << a.accepted << ",\"value\":" << a.value
                      << ",\"worker_has_secret\":" << a.worker_has_secret;
        } catch (const std::invalid_argument& e) {
            if (std::string(e.what())!="input domain") throw;
            std::cout << ",\"status\":\"input_rejected\"";
        } catch (const std::exception& e) {
            std::cerr << e.what() << '\n';
            std::cout << ",\"status\":\"setup_error\"";
        }
        std::cout << "}\n";
    }
}
