#include <iostream>
#include <fstream>
#include <string>

using namespace std;

void read_file(ifstream& file, int position, int n, string& content)
{
    file.seekg(position);
    content.resize(n);
    file.read(&content[0], n);
}

int main(int argc, char* argv[])
{
    string filename = "random_file.txt"; // default filename
    int default_n = 4096;                // default number of characters to read

    for (int i = 1; i < argc; i++)
    {
        string arg = argv[i];
        if (arg == "-f" && i + 1 < argc)
        {
            filename = argv[i + 1];
            i++;
        }
        else if (arg == "-n" && i + 1 < argc)
        {
            default_n = stoi(argv[i + 1]);
            i++;
        }
    }

    ifstream file(filename);
    if (!file.is_open())
    {
        cout << "Error: Cannot open file " << filename << endl;
        exit(EXIT_FAILURE);
    }

    int position = 0;
    while (true)
    {
        string input;
        cout << "Enter the number of characters to display (default is 4k, -1 to exit): ";
        getline(cin, input);
        int n;
        if (input.empty())
            n = default_n;
        else
            n = stoi(input);
        if (n == -1)
            break;
        string next_text;
        read_file(file, position, n, next_text);
        position += n;
        string next_preview;
        read_file(file, position, 20, next_preview);
        cout << next_text << endl;
        cout << endl;
        cout << "Preview to the next 20 characters: " << next_preview << endl;
        cout << endl;
    }
    file.close();
    return 0;
}
