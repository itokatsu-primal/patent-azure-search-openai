import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "リチウム硫黄電池における主な技術課題は何ですか。",
        value: "リチウム硫黄電池における主な技術課題は何ですか。"
    },
    { text: "リチウム硫黄電が優れている点は何ですか。", value: "リチウム硫黄電が優れている点は何ですか。" },
    { text: "リチウム硫黄電は何の用途で利用されていますか。", value: "リチウム硫黄電は何の用途で利用されていますか。" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
