package com.litianyi.entity;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/24 08:46
 * @Description:
 */
public class FIleasd {

    private String name;
    private int age;
    private Student student;

    public FIleasd(String name, int age) {
        this.name = name;
        this.age = age;
        this.student = new Student(name,age);
    }

    public  void finsa() {
        student.say();
    }

    public static void main(String[] args) {
        FIleasd a = new FIleasd("张三", 12);
        a.finsa();

        FIleasd b = new FIleasd("李四", 14);
        b.finsa();



    }


}
