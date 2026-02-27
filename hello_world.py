print("Hello, World!")

def is_palindrome(s):
    return s == s[::-1]

# Test the palindrome function
test_string = "racecar"
print(f"'{test_string}' is palindrome: {is_palindrome(test_string)}")

test_string = "hello"
print(f"'{test_string}' is palindrome: {is_palindrome(test_string)}")