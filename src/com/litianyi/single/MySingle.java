package com.litianyi.single;

import java.util.ArrayList;
import java.util.List;

/**
 * @Auther: ICC18e697
 * @Date: 2018/11/21 20:20
 * @Description:
 */
public class MySingle {

    private String name;

    List<String> names = new ArrayList<>();

    private MySingle() {
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    private static class InnerClaa{
        private static final MySingle mySingle=new MySingle();
    }

    public static MySingle getMysingle(){
        return InnerClaa.mySingle;
    }


    public String addSomeThings (String name) {
            names.add(name);
        int size = names.size();
        System.out.println(size);
        if (size>=2){
            return "数组大于2了";
        }
        return "数组还没到2";
    }


    public static void main(String[] args) {
        MySingle mysingle = MySingle.getMysingle();
        MySingle mysingle2 = MySingle.getMysingle();

        System.out.println(mysingle==mysingle2);
    }



}
