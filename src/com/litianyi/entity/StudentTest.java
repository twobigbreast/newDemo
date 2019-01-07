package com.litianyi.entity;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.Set;

/**
 * @Auther: ICC18e697
 * @Date: 2019/1/2 09:32
 * @Description:
 */
public class StudentTest {


    public static void main(String[] args) {
        Student student1 = new Student("张三",17);
        Student student2 = new Student("李四",18);
        Student student3 = new Student("王五",19);
        Student student4 = new Student("赵六",20);
        ArrayList<Student> students = new ArrayList<>();
        students.add(student1);
        students.add(student2);
        students.add(student3);
        students.add(student4);
        students.add(student2);
        Set<Student> set = new HashSet<>(students);
        for (Student student : set) {
            System.out.println(student);
        }

    }

}
