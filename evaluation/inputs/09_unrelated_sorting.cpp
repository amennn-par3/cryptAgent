#include <algorithm>
#include <vector>
std::vector<int> sorted(std::vector<int> values) {
    std::sort(values.begin(), values.end());
    return values;
}
