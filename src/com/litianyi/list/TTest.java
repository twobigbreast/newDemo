package com.litianyi.list;

import java.util.ArrayList;

/**
 * @Auther: ICC18e697
 * @Date: 2018/12/20 14:51
 * @Description:
 */
public class TTest {
    public static void main(String[] args) {
        ArrayList<Integer> list = new ArrayList<>(3500);
        MyList myList1 = new MyList(list);
        MyList myList2 = new MyList(list);
        MyList myList3 = new MyList(list);
        MyList myList4 = new MyList(list);
        new Thread(myList1).start();
        new Thread(myList2).start();
        new Thread(myList3).start();
        new Thread(myList4).start();

    }
}
