#include <iostream>
#include <fstream>
#include <string>

using namespace std;

string read_file(string filename) {
    ifstream file(filename);
    if (!file.is_open()) {
        cout << "Error: Cannot open file " << filename << endl;
        exit(EXIT_FAILURE);
    }
    string content((istreambuf_iterator<char>(file)), (istreambuf_iterator<char>()));
    file.close();
    return content;
}

int main() {
    string filename = "random_file.txt"; // replace with the name of your file
    string text = read_file(filename);
    int position = 0;
    int default_n = 4096;
    while (true) {
        string input;
        cout << "Enter the number of characters to display (default is 4k): ";
        getline(cin, input);
        int n;
        if (input.empty()) {
            n = default_n;
        } else {
            n = stoi(input);
        }
        if (n == -1) {
            break;
        }
        string next_text = text.substr(position, n);
        string next_preview = text.substr(position+n, 20);
        cout << next_text << endl;
        cout << "Preview to the next 20 characters: " << next_preview << endl;
        position += n;
    }
    return 0;
}
