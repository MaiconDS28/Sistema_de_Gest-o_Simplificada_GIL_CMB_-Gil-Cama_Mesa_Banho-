document.addEventListener("DOMContentLoaded", function () {
    const selectProduto = document.getElementById("id_produto");
    const inputQuantidade = document.getElementById("quantidade");
    const selectTipo = document.getElementById("tipo_registro");
    const visorTotal = document.getElementById("visor_valor_total");
    const alertaValidacao = document.getElementById("alerta_validacao_cliente");
    const textoValidacao = document.getElementById("texto_validacao_cliente");
    const btnConfirmar = document.getElementById("btn_confirmar_lancamento");

    function atualizarCalculoEValidacao() {
        if (!selectProduto || !inputQuantidade || !visorTotal) return;
        const opcao = selectProduto.options[selectProduto.selectedIndex];
        const preco = parseFloat(opcao ? opcao.getAttribute("data-preco") || "0" : "0");
        const estoque = parseInt(opcao ? opcao.getAttribute("data-estoque") || "0" : "0", 10);
        const nomeProduto = opcao ? opcao.getAttribute("data-nome") || "produto" : "produto";
        const qtd = parseInt(inputQuantidade.value || "0", 10);
        const tipo = selectTipo ? selectTipo.value : "fiado";

        if (preco > 0 && qtd > 0) {
            const total = (preco * qtd).toFixed(2).replace(".", ",");
            visorTotal.textContent = "Valor Total Calculado: R$ " + total;
        } else {
            visorTotal.textContent = "Valor Total Calculado: R$ 0,00";
        }

        if (alertaValidacao && textoValidacao) {
            if (qtd > 0 && tipo === "fiado" && opcao && opcao.value !== "" && qtd > estoque) {
                alertaValidacao.classList.remove("d-none");
                textoValidacao.textContent =
                    "[!] Atenção: A quantidade digitada (" + qtd + " un.) é maior que o estoque disponível de '" +
                    nomeProduto + "' (" + estoque + " un.). Digite até " + estoque + " un.";
                if (btnConfirmar) btnConfirmar.disabled = true;
            } else {
                alertaValidacao.classList.add("d-none");
                if (btnConfirmar) btnConfirmar.disabled = false;
            }
        }
    }

    if (selectProduto) selectProduto.addEventListener("change", atualizarCalculoEValidacao);
    if (inputQuantidade) inputQuantidade.addEventListener("input", atualizarCalculoEValidacao);
    if (selectTipo) selectTipo.addEventListener("change", atualizarCalculoEValidacao);
    atualizarCalculoEValidacao();
});
