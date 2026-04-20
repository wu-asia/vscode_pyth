#include<iostream>
#include<string>
using namespace std;

void get_pi(string s, int pi[])
{
    int n = s.size();
    s = " " + s;
    for(int i = 2; i <= n; i++)
    {
        int j = pi[i - 1];
        while(j && s[j + 1] != s[i]) j = pi[j];
        if(s[j + 1] == s[i]) j++;
        pi[i] = j;
    }
}

void kmp(string sub, string s)
{
    int m = sub.size();
    string new_s = sub + "#" + s;
    int n = new_s.size();
    new_s = " " + new_s;
    int pi[1000] = {0};
    for(int i = 2; i <= n; i++)
    {
        int j = pi[i - 1];
        while(j && new_s[j + 1] != new_s[i]) j = pi[j];
        if(s[j + 1] == s[i]) j++;
        pi[i] = j;
        if(pi[i] == m)
            cout << i - 2 * m << " ";
    }
    cout << endl;
}
int main()
{
    // string s = "abab";
    // int pi[100] = {0};
    // get_pi(s, pi);
    // int n = s.size();
    // for(int i = 1; i <= n; i++)
    //     cout << pi[i] << " ";
    // cout << endl;
    string sub, s;
    cin >> sub >> s;
    int pi[1000] = {0};
    

    return 0;
}