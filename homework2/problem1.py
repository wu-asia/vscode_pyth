
import pickle

txt_file_path = "D:/test.txt"

pickle_file_path = "D:/test_pickle.dat" 

with open(txt_file_path, 'r', encoding='utf-8') as f:
    txt_data = f.read() #读文件中的内容

with open(pickle_file_path, 'wb') as f:
    pickle.dump(txt_data, f)

with open(pickle_file_path, 'rb') as f:
    data = pickle.load(f)

print(data)
