import { createGlobalStyle } from "antd-style";
import { ConfigProvider, bailianTheme } from "@agentscope-ai/design";
import { BrowserRouter } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import "./styles/layout.css";
import "./styles/form-override.css";
import zhCN from "antd/locale/zh_CN";

const GlobalStyle = createGlobalStyle`
* {
  margin: 0;
  box-sizing: border-box;
}
`;

// 自定义分页国际化
const customZhCN = {
  ...zhCN,
  Pagination: {
    ...zhCN.Pagination,
    items_per_page: '条/页',
  },
};

function App() {
  return (
    <BrowserRouter>
      <GlobalStyle />
      <ConfigProvider {...bailianTheme} prefix="copaw" prefixCls="copaw" locale={customZhCN}>
        <MainLayout />
      </ConfigProvider>
    </BrowserRouter>
  );
}

export default App;
