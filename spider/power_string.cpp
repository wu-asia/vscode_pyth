#include<iostream>
#include<string>
using namespace std;
const int N = 1e6 + 10;
int pi[N];
int func(string s)
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
    if(n % (n - pi[n]) == 0) return 1;
    else return n / (n - pi[n]);
}
int main()
{
    string s;
   
        /* code */
        while(cin >> s)
        {
            if(s == ".")
                break;
            cout << func(s) << endl;
        }
        
    
    return 0;
}