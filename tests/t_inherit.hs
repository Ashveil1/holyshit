class Animal:
  def __init__(self, name):
    self.name = name
  def speak(self):
    return "..."
  def intro(self):
    return self.name + " says " + self.speak()
class Dog(Animal):
  def speak(self):
    return "woof"
class Puppy(Dog):
  def __init__(self, name, age):
    Animal__init__(self, name)
    self.age = age
  def speak(self):
    return "yip"
a = Animal("cat")
d = Dog("rex")
p = Puppy("bit", 1)
print a.intro()
print d.intro()
print p.intro()
print p.age
